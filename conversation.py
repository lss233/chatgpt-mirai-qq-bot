import contextlib
import time
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from EdgeGPT.EdgeGPT import ConversationStyle
from graia.amnesia.message import MessageChain
from graia.ariadne.message.element import Image as GraiaImage, Element
from loguru import logger

from adapter.baidu.yiyan import YiyanAdapter
from adapter.botservice import BotAdapter
from adapter.chatgpt.api import ChatGPTAPIAdapter
from adapter.chatgpt.web import ChatGPTWebAdapter
from adapter.claude.slack import ClaudeInSlackAdapter
from adapter.google.bard import BardAdapter
from adapter.gpt4free.g4f_helper import parse as g4f_parse
from adapter.gpt4free.gpt4free import Gpt4FreeAdapter
from adapter.ms.bing import BingAdapter
from adapter.quora.poe import PoeBot, PoeAdapter
from adapter.thudm.chatglm_6b import ChatGLM6BAdapter
from adapter.xunfei.xinghuo import XinghuoAdapter
from constants import LlmName
from constants import config
from drawing import DrawingAPI, SDWebUI as SDDrawing, OpenAI as OpenAIDrawing
from exceptions import PresetNotFoundException, BotTypeNotFoundException, NoAvailableBotException, \
    CommandRefusedException, DrawingFailedException
from middlewares.draw_ratelimit import MiddlewareRatelimit
from renderer import Renderer
from renderer.merger import BufferedContentMerger, LengthContentMerger
from renderer.renderer import MixedContentMessageChainRenderer, MarkdownImageRenderer, PlainTextRenderer
from renderer.splitter import MultipleSegmentSplitter
from utils import retry
from utils.text_to_speech import TtsVoice, TtsVoiceManager

handlers = {}

middlewares = MiddlewareRatelimit()


class ConversationContext:
    type: str
    adapter: BotAdapter
    """聊天机器人适配器"""

    splitter: Renderer
    """消息分隔器"""
    merger: Renderer
    """消息合并器"""
    renderer: Renderer
    """消息渲染器"""

    drawing_adapter: DrawingAPI = None
    """绘图引擎"""

    preset: str = None

    preset_decoration_format: Optional[str] = "{prompt}"
    """预设装饰文本"""

    conversation_voice: TtsVoice = None
    """语音音色"""

    @property
    def current_model(self):
        return self.adapter.current_model

    @property
    def supported_models(self):
        return self.adapter.supported_models

    def __init__(self, _type: str, session_id: str):
        self.session_id = session_id

        self.last_resp = ''

        self.last_resp_time = -1

        self.switch_renderer()

        if config.text_to_speech.always:
            tts_engine = config.text_to_speech.engine
            tts_voice = config.text_to_speech.default
            try:
                self.conversation_voice = TtsVoiceManager.parse_tts_voice(tts_engine, tts_voice)
            except KeyError as e:
                logger.error(f"Failed to load {tts_engine} tts voice setting -> {tts_voice}")
        if _type == LlmName.ChatGPT_Web.value:
            self.adapter = ChatGPTWebAdapter(self.session_id)
        elif _type == LlmName.ChatGPT_Api.value:
            self.adapter = ChatGPTAPIAdapter(self.session_id)
        elif PoeBot.parse(_type):
            self.adapter = PoeAdapter(self.session_id, PoeBot.parse(_type))
        elif _type == LlmName.Bing.value:
            self.adapter = BingAdapter(self.session_id)
        elif _type == LlmName.BingC.value:
            self.adapter = BingAdapter(self.session_id, ConversationStyle.creative)
        elif _type == LlmName.BingB.value:
            self.adapter = BingAdapter(self.session_id, ConversationStyle.balanced)
        elif _type == LlmName.BingP.value:
            self.adapter = BingAdapter(self.session_id, ConversationStyle.precise)
        elif _type == LlmName.Bard.value:
            self.adapter = BardAdapter(self.session_id)
        elif _type == LlmName.YiYan.value:
            self.adapter = YiyanAdapter(self.session_id)
        elif _type == LlmName.ChatGLM.value:
            self.adapter = ChatGLM6BAdapter(self.session_id)
        elif _type == LlmName.SlackClaude.value:
            self.adapter = ClaudeInSlackAdapter(self.session_id)
        elif _type == LlmName.XunfeiXinghuo.value:
            self.adapter = XinghuoAdapter(self.session_id)
        elif g4f_parse(_type):
            self.adapter = Gpt4FreeAdapter(self.session_id, g4f_parse(_type))
        else:
            raise BotTypeNotFoundException(_type)
        self.type = _type

        # 没有就算了
        if config.sdwebui:
            self.drawing_adapter = SDDrawing()
        elif config.bing.use_drawing:
            with contextlib.suppress(NoAvailableBotException):
                self.drawing_adapter = BingAdapter(self.session_id, ConversationStyle.creative)
        else:
            with contextlib.suppress(NoAvailableBotException):
                self.drawing_adapter = OpenAIDrawing(self.session_id)

    def switch_renderer(self, mode: Optional[str] = None):
        # 目前只有这一款
        self.splitter = MultipleSegmentSplitter()

        if config.response.buffer_delay > 0:
            self.merger = BufferedContentMerger(self.splitter)
        else:
            self.merger = LengthContentMerger(self.splitter)

        if not mode:
            mode = "image" if config.text_to_image.default or config.text_to_image.always else config.response.mode

        if mode == "image" or config.text_to_image.always:
            self.renderer = MarkdownImageRenderer(self.merger)
        elif mode == "mixed":
            self.renderer = MixedContentMessageChainRenderer(self.merger)
        elif mode == "text":
            self.renderer = PlainTextRenderer(self.merger)
        else:
            self.renderer = MixedContentMessageChainRenderer(self.merger)
        if mode != "image" and config.text_to_image.always:
            raise CommandRefusedException("不要！由于配置文件设置强制开了图片模式，我不会切换到其他任何模式。")

    async def reset(self):
        await self.adapter.on_reset()
        self.last_resp = ''
        self.last_resp_time = -1
        # 在重置会话时自动加载默认预设
        async for value in self.load_preset('default'):
            pass
        yield config.response.reset

    @retry((httpx.ConnectError, httpx.ConnectTimeout, TimeoutError))
    async def ask(self, prompt: str, chain: MessageChain = None, name: str = None):
        await self.check_and_reset()
        # 检查是否为 画图指令
        for prefix in config.trigger.prefix_image:
            if prompt.startswith(prefix) and not isinstance(self.adapter, YiyanAdapter):
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
            async for item in self.adapter.ask(prompt):
                if isinstance(item, Element):
                    yield item
                else:
                    yield await self.renderer.render(item)
                self.last_resp = item or ''
                self.last_resp_time = int(time.time())
            yield await self.renderer.result()

    async def rollback(self):
        resp = await self.adapter.rollback()
        if isinstance(resp, bool):
            yield config.response.rollback_success if resp else config.response.rollback_fail.format(
                reset=config.trigger.reset_command)
        else:
            yield resp

    async def switch_model(self, model_name):
        return await self.adapter.switch_model(model_name)

    async def load_preset(self, keyword: str):
        self.preset_decoration_format = None
        if keyword in config.presets.keywords:
            presets = config.load_preset(keyword)
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

                    if role == 'voice':
                        self.conversation_voice = TtsVoiceManager.parse_tts_voice(config.text_to_speech.engine,
                                                                                  text.strip())
                        logger.debug(f"Set conversation voice to {self.conversation_voice.full_name}")
                        continue
                    
                    # Replace {date} in system prompt
                    text = text.replace("{date}", datetime.now().strftime('%Y-%m-%d'))
                    async for item in self.adapter.preset_ask(role=role.lower().strip(), text=text.strip()):
                        yield item
        elif keyword != 'default':
            raise PresetNotFoundException(keyword)
        self.preset = keyword

    def delete_message(self, respond_msg):
        # TODO: adapt to all platforms
        pass

    async def check_and_reset(self):
        timeout_seconds = config.system.auto_reset_timeout_seconds
        current_time = time.time()
        if timeout_seconds == -1 or self.last_resp_time == -1 or current_time - self.last_resp_time < timeout_seconds:
            return
        logger.debug(f"Reset conversation({self.session_id}) after {current_time - self.last_resp_time} seconds.")
        async for _resp in self.reset():
            logger.debug(_resp)


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
