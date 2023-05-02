from datetime import datetime
from typing import List, Dict, Optional

import httpx
from graia.amnesia.message import MessageChain
from graia.ariadne.message.element import Image as GraiaImage, Element
from loguru import logger

import constants
from framework.drawing import DrawAI, DrawingAIFactory
from framework.exceptions import PresetNotFoundException, CommandRefusedException, DrawingFailedException
from framework.llm import LlmFactory
from framework.llm.baidu.yiyan import YiyanAdapter
from framework.llm.llm import Llm
from framework.middlewares.draw_ratelimit import MiddlewareRatelimit
from framework.renderer import Renderer
from framework.renderer.merger import BufferedContentMerger, LengthContentMerger
from framework.renderer.renderer import MixedContentMessageChainRenderer, MarkdownImageRenderer, PlainTextRenderer
from framework.renderer.splitter import MultipleSegmentSplitter
from framework.tts import TTSEngine, TTSVoice
from framework.utils import retry

handlers = {}

middlewares = MiddlewareRatelimit()


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

    def switch_tts_engine(self, name: Optional[str] = None):
        self.tts_engine = TTSEngine.get_engine(name)
        self.conversation_voice = self.tts_engine.choose_voice(config.text_to_speech.default)

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
        yield constants.config.response.reset

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

        if self.preset_decoration_format:
            prompt = (
                self.preset_decoration_format.replace("{prompt}", prompt)
                .replace("{nickname}", name)
                .replace("{last_resp}", self.last_resp)
                .replace("{date}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )

        async with self.renderer:
            async for item in self.llm_adapter.ask(prompt):
                if isinstance(item, Element):
                    yield item
                else:
                    yield await self.renderer.render(item)
                self.last_resp = item or ''
            yield await self.renderer.result()

    async def rollback(self):
        return await self.llm_adapter.rollback()

    async def switch_model(self, model_name):
        return await self.llm_adapter.switch_model(model_name)

    async def load_preset(self, keyword: str):
        self.preset_decoration_format = None
        if keyword in constants.config.presets.keywords:
            presets = constants.config.load_preset(keyword)
            for text in presets:
                if not text.strip() or not text.startswith('#'):
                    # 判断格式是否为 role: 文本
                    if ':' in text:
                        role, text = text.split(':', 1)
                    else:
                        role = 'system'

                    if role == 'user_send':
                        self.preset_decoration_format = text
                        continue

                    if role == 'voice' and self.tts_engine:
                        self.conversation_voice = await self.tts_engine.choose_voice(text.strip())
                        logger.debug(f"Set conversation voice to {self.conversation_voice.full_name}")
                        continue

                    async for item in self.llm_adapter.preset_ask(role=role.lower().strip(), text=text.strip()):
                        yield item
        elif keyword != 'default':
            raise PresetNotFoundException(keyword)
        self.preset = keyword

    def delete_message(self, respond_msg):
        # TODO: adapt to all platforms
        pass

    async def init(self):
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
        await conversation.init()
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
