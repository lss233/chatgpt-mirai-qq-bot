from typing import Generator

from loguru import logger

from adapter.botservice import BotAdapter
from revChatGPT.V3 import Chatbot as OpenAIChatbot

from config import OpenAIAPIKey
from constants import botManager

class ChatGPTAPIAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None
    """API Key"""


    bot: OpenAIChatbot = None
    """实例"""

    def __init__(self):
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(api_key=self.api_info.api_key)
        self.conversation_id = None
        self.parent_id = None
        super().__init__()

    async def rollback(self):
        if len(self.bot.conversation) > 0:
            self.bot.rollback()
            return True
        else:
            return False

    async def on_reset(self):
        self.bot.conversation = []

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        full_response = ''
        for content in self.bot.ask_stream(prompt):
            full_response += content
            logger.debug("[ChatGPT-API] 响应：" + content)
            yield full_response

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role == 'chatgpt':
            logger.debug(f"[预设] 响应：{text}")
            yield text
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        self.bot.conversation.append({"role": role, "content": text})

