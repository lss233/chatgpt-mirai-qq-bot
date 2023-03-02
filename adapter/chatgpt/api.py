from typing import Generator

from adapter.botservice import BotAdapter
from revChatGPT.V3 import Chatbot as OpenAIChatbot
from manager.bot import BotManager


class ChatGPTAPIAdapter(BotAdapter):
    conversation: list = []
    """聊天记录"""

    bot: OpenAIChatbot
    """实例"""

    def __int__(self):
        self.bot = BotManager.pick('chatgpt-api')

    async def rollback(self):
        self.bot.rollback()
        self.conversation = self.bot.conversation

    async def on_reset(self): ...

    async def ask(self, prompt: str) -> Generator[str]:
        self.bot.conversation = self.conversation
        yield self.bot.ask_stream(prompt=prompt)
        self.conversation = self.bot.conversation
