from typing import Generator

import aiohttp

from adapter.botservice import BotAdapter
from bots.openai.api import OpenAIAPIBot

class ChatGPTAPIAdapter(BotAdapter):
    conversations: list = []
    """聊天记录"""

    bot: OpenAIAPIBot
    """实例"""


    def __int__(self):
        self.bot = OpenAIAPIBot.pick()


    async def rollback(self): ...

    async def reset(self): ...

    async def ask(self, msg: str) -> Generator[str]: ...