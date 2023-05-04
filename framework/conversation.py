from typing import List, Dict, Optional, Callable, Any
import re
import httpx
from graia.amnesia.message import MessageChain
from graia.ariadne.message.element import Image as GraiaImage, Element
from functools import partial

import constants
from framework.drawing import DrawAI, DrawingAIFactory
from framework.exceptions import PresetNotFoundException, CommandRefusedException, DrawingFailedException, \
    BotTypeNotFoundException, NoAvailableBotException
from framework.llm import LlmFactory
from framework.llm.baidu.yiyan import YiyanAdapter
from framework.llm.llm import Llm
from framework.middlewares.draw_ratelimit import MiddlewareRatelimit
from framework.prompt_engine import PromptFlowBaseModel, PromptFlowUnsupportedException, load_prompt, \
    execute_action_block
from framework.renderer import Renderer
from framework.renderer.merger import BufferedContentMerger, LengthContentMerger
from framework.renderer.renderer import MixedContentMessageChainRenderer, MarkdownImageRenderer, PlainTextRenderer
from framework.renderer.splitter import MultipleSegmentSplitter
from framework.tts import TTSEngine, TTSVoice
from framework.utils import retry
from loguru import logger

handlers = {}

middlewares = MiddlewareRatelimit()


class AsyncPromptExecutionContext:
    conversation: "ConversationContext"

    actions: Dict[str, Callable] = {}
    """操作"""

    variables: Dict[str, Any] = {}
    """变量"""

    flow: PromptFlowBaseModel

    def __init__(self, conversation: "ConversationContext", variables: Dict[str, Any], actions: Dict[str, Callable]):
        self.conversation = conversation
        self.actions = actions.copy()
        self.variables = variables.copy()
        self.flow = conversation.prompt_flow
        self.actions['system/use-tts-engine'] = lambda engine, voice: self.conversation.switch_tts_engine(engine, voice)
        self.actions['system/prompt'] = lambda role, prompt: self.conversation.llm_adapter.preset_ask(role, prompt)
        self.actions['system/text'] = lambda text: text
        self.actions['system/text-extraction'] = lambda text, pattern: [m.groupdict() for m in re.finditer(pattern, text, re.RegexFlag.M)]
        self.actions['system/instant-ask'] = partial(AsyncPromptExecutionContext.instant_ask, self)
        self.actions['tts/parse_emotion_text'] = TTSEngine.parse_emotion_text
        self.actions['tts/speak'] = lambda text: self.conversation.tts_engine.speak(text, self.conversation.conversation_voice)

    async def init(self):
        await execute_action_block(self.flow.init, self.variables, self.actions)

    async def input(self, prompt):
        self.variables["input"] = {
            "message": prompt
        }
        await execute_action_block(self.flow.input, self.variables, self.actions)
        async with self.conversation.merger as merger:
            async for item in self.conversation.llm_adapter.ask(self.variables["input"]["message"]):
                if not item:
                    continue
                if isinstance(item, Element):
                    await self.actions["system/user_message"](item)
                    continue
                if merged := await merger.render(item):
                    self.variables["output"] = {
                        "message": str(merged),
                        "finished": False
                    }
                    await execute_action_block(self.flow.output, self.variables, self.actions)
                    await self.actions["system/user_message"](text=self.variables["output"]["message"])

            merged = await merger.result()
            self.variables["output"] = {
                "message": str(merged),
                "finished": True
            }
            await execute_action_block(self.flow.output, self.variables, self.actions)
            await self.actions["system/user_message"](text=self.variables["output"]["message"])

    async def instant_ask(self, supported_llms, prompt):
        logger.info(f"[Instant ask] session_id={self.conversation.session_id}, prompt={prompt}")
        exc = None
        for llm_name in supported_llms:
            try:
                llm_instance = LlmFactory.create(name=llm_name, session_id=self.conversation.session_id)
                break
            except (BotTypeNotFoundException, NoAvailableBotException) as e:
                exc = e
                continue
        else:
            raise NoAvailableBotException(supported_llms) from exc
        everything = ''
        async for item in llm_instance.ask(prompt):
            everything = item
        logger.info(f'[Instant ask] response = {everything}')
        return everything


class ConversationContext:
    type: str

    llm_adapter: Llm
    """语言模型适配器"""

    drawing_adapter: Optional[DrawAI] = None
    """绘图引擎适配器"""

    tts_engine: Optional[TTSEngine] = None
    """文字转语音引擎"""

    splitter: Renderer
    """消息分隔器"""
    merger: Renderer
    """消息合并器"""
    renderer: Renderer
    """消息渲染器"""

    conversation_voice: Optional[TTSVoice] = None
    """语音音色"""

    preset: str = None
    """预设"""

    prompt_flow: Optional[PromptFlowBaseModel] = PromptFlowBaseModel(name="default", author="lss233")
    """交互流"""

    execution_variables: Dict[str, Any] = {
        "input": {},
        "user": {},
        "output": {},
        "tts_engine": {}
    }

    execution_actions: Dict[str, Callable] = {}

    preset_decoration_format: Optional[str] = "{prompt}"
    """预设装饰文本"""

    @property
    def current_model(self):
        return self.llm_adapter.current_model

    @property
    def supported_models(self):
        return self.llm_adapter.supported_models

    def __init__(self, _type: str, session_id: str):

        self.session_id = session_id
        self.type = _type
        self.last_resp = ''

        self.switch_renderer()
        self.switch_drawing_ai()

        self.llm_adapter = LlmFactory.create(name=_type, session_id=session_id)

    def switch_drawing_ai(self, name: Optional[str] = None):
        self.drawing_adapter = DrawingAIFactory.create(name)

    def switch_tts_engine(self, name: Optional[str] = None, voice = None):
        self.tts_engine = TTSEngine.get_engine(name)
        self.conversation_voice = self.tts_engine.choose_voice(voice or constants.config.text_to_speech.default)
        self.execution_variables["tts_engine"] = {
            "emotions": self.tts_engine.get_supported_styles(),
            "voice": self.conversation_voice.codename
        }

    def switch_renderer(self, mode: Optional[str] = None):
        # 目前只有这一款
        self.splitter = MultipleSegmentSplitter()

        if constants.config.response.buffer_delay > 0:
            self.merger = BufferedContentMerger(self.splitter)
        else:
            self.merger = LengthContentMerger(self.splitter)

        if not mode:
            mode = "image" if constants.config.text_to_image.default or constants.config.text_to_image.always else constants.config.response.mode

        if mode == "image" or constants.config.text_to_image.always:
            self.renderer = MarkdownImageRenderer(self.merger)
        elif mode == "mixed":
            self.renderer = MixedContentMessageChainRenderer(self.merger)
        elif mode == "text":
            self.renderer = PlainTextRenderer(self.merger)
        else:
            self.renderer = MixedContentMessageChainRenderer(self.merger)
        if mode != "image" and constants.config.text_to_image.always:
            # TODO: export to config
            raise CommandRefusedException("不要！由于配置文件设置强制开了图片模式，我不会切换到其他任何模式。")

    async def reset(self):
        # 重建一个新的 LLM 实例
        await self.llm_adapter.on_destoryed()
        self.llm_adapter = LlmFactory.create(name=self.type, session_id=self.session_id)
        self.last_resp = ''

    @retry((httpx.ConnectError, httpx.ConnectTimeout, TimeoutError))
    async def ask(self, prompt: str, chain: MessageChain = None, name: str = None):
        # 检查是否为 画图指令
        for prefix in constants.config.trigger.prefix_image:
            if prompt.startswith(prefix) and not isinstance(self.llm_adapter, YiyanAdapter):
                # TODO(lss233): 此部分可合并至 RateLimitMiddleware
                respond_str = middlewares.handle_draw_request(self.session_id, prompt)
                # TODO(lss233): 这什么玩意
                if respond_str != "1":
                    yield respond_str
                    return
                if not self.drawing_adapter:
                    yield "未配置画图引擎，无法使用画图功能！"
                    return
                prompt = prompt.removeprefix(prefix)
                try:
                    if chain.has(GraiaImage):
                        images = await self.drawing_adapter.img_to_img(chain.get(GraiaImage), prompt)
                    else:
                        images = await self.drawing_adapter.text_to_img(prompt)
                    for i in images:
                        yield i
                except Exception as e:
                    raise DrawingFailedException from e
                respond_str = middlewares.handle_draw_respond_completed(self.session_id, prompt)
                if respond_str != "1":
                    yield respond_str
                return

        async with self.renderer:
            async for item in self.llm_adapter.ask(prompt):
                if isinstance(item, Element):
                    yield item
                else:
                    yield await self.renderer.render(item)
            yield await self.renderer.result()

    async def rollback(self):
        return await self.llm_adapter.rollback()

    async def switch_model(self, model_name):
        return await self.llm_adapter.switch_model(model_name)

    async def load_prompt(self, prompt_flow: PromptFlowBaseModel):
        if self.type not in prompt_flow.supported_llms:
            raise PromptFlowUnsupportedException(self.type, prompt_flow.supported_llms)
        await self.reset()
        self.prompt_flow = prompt_flow

    async def load_preset(self, keyword: str):
        self.preset_decoration_format = None
        if keyword in constants.config.prompts.keywords:
            prompt_flow = load_prompt(constants.config.prompts.keywords[keyword])
            await self.load_prompt(prompt_flow)
        elif keyword != 'default':
            raise PresetNotFoundException(keyword)
        self.preset = keyword

    def delete_message(self, respond_msg):
        # TODO: adapt to all platforms
        pass

    async def __aenter__(self):
        return AsyncPromptExecutionContext(self, self.execution_variables, self.execution_actions)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class ConversationHandler:
    """
    每个聊天窗口拥有一个 ConversationHandler，
    负责管理多个不同的 ConversationContext
    """
    conversations: Dict[str, ConversationContext]
    """当前聊天窗口下所有的会话"""

    current_conversation: ConversationContext = None

    session_id: str = 'unknown'

    def __init__(self, session_id: str):
        self.conversations = {}
        self.session_id = session_id

    def list(self) -> List[ConversationContext]:
        ...

    """
    获取或创建新的上下文
    这里的代码和 create 是一样的
    因为 create 之后会加入多会话功能
    """

    async def first_or_create(self, _type: str):
        if _type in self.conversations:
            return self.conversations[_type]
        conversation = ConversationContext(_type, self.session_id)
        self.conversations[_type] = conversation
        return conversation

    """创建新的上下文"""

    async def create(self, _type: str):
        if _type in self.conversations:
            return self.conversations[_type]
        conversation = ConversationContext(_type, self.session_id)
        self.conversations[_type] = conversation
        return conversation

    """切换对话上下文"""

    def switch(self, index: int) -> bool:
        if len(self.conversations) > index:
            self.current_conversation = self.conversations[index]
            return True
        return False

    @classmethod
    async def get_handler(cls, session_id: str):
        if session_id not in handlers:
            handlers[session_id] = ConversationHandler(session_id)
        return handlers[session_id]
