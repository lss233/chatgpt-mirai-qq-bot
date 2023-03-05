from typing import List, Dict

from EdgeGPT import ConversationStyle

from adapter.botservice import BotAdapter
from adapter.chatgpt.api import ChatGPTAPIAdapter
from adapter.chatgpt.web import ChatGPTWebAdapter
from adapter.ms.bing import BingAdapter
from constants import config
from exceptions import PresetNotFoundException, BotTypeNotFoundException
from renderer.renderer import Renderer, FullTextRenderer, MarkdownImageRenderer

handlers = dict()


class ConversationContext:
    type: str
    adapter: BotAdapter
    renderer: Renderer
    preset: str = None

    def __init__(self, _type: str, session_id: str):
        self.session_id = session_id

        if config.text_to_image.default:
            self.renderer = MarkdownImageRenderer()
        else:
            self.renderer = FullTextRenderer()
        if _type == 'chatgpt-web':
            self.adapter = ChatGPTWebAdapter(self.session_id)
        elif _type == 'chatgpt-api':
            self.adapter = ChatGPTAPIAdapter(self.session_id)
        elif _type == 'bing':
            self.adapter = BingAdapter(self.session_id)
        elif _type == 'bing-c':
            self.adapter = BingAdapter(self.session_id, ConversationStyle.creative)
        elif _type == 'bing-b':
            self.adapter = BingAdapter(self.session_id, ConversationStyle.balanced)
        elif _type == 'bing-p':
            self.adapter = BingAdapter(self.session_id, ConversationStyle.precise)
        else:
            raise BotTypeNotFoundException(_type)
        self.type = _type

    async def reset(self):
        await self.adapter.on_reset()
        yield config.response.reset

    async def ask(self, prompt: str, name: str = None):
        async with self.renderer:
            async for item in self.adapter.ask(prompt):
                yield await self.renderer.render(item)
            yield await self.renderer.result()

    async def rollback(self):
        resp = await self.adapter.rollback()
        if isinstance(resp, bool):
            yield config.response.rollback_success if resp else config.response.rollback_fail.format(reset=config.trigger.reset_command)
        else:
            yield resp

    async def load_preset(self, keyword: str):
        if keyword not in config.presets.keywords:
            if not keyword == 'default':
                raise PresetNotFoundException(keyword)
        else:
            presets = config.load_preset(keyword)
            for text in presets:
                if text.startswith('#'):
                    continue
                else:
                    # 判断格式是否为 role: 文本
                    if ':' in text:
                        role, text = text.split(':', 1)
                    else:
                        role = 'system'
                    async for item in self.adapter.preset_ask(role=role.lower().strip(), text=text.strip()):
                        yield item
        self.preset = keyword


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
        self.conversations = dict()
        self.session_id = session_id

    def list(self) -> List[ConversationContext]:
        ...

    """创建新的上下文"""

    async def create(self, _type: str):
        if _type in self.conversations:
            return self.conversations[_type]
        else:
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
