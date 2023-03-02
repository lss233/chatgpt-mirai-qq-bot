from typing import Generator

from adapter.botservice import BotAdapter
from EdgeGPT import ChatHub as EdgeChatbot
from manager.bot import BotManager


class BingAdapter(BotAdapter):
    bot: EdgeChatbot
    """实例"""

    def __int__(self):
        self.bot = BotManager.pick('bing')

    async def rollback(self):
        raise NotImplemented

    async def on_reset(self): ...

    async def ask(self, prompt: str) -> Generator[str]:
        await self.bot.ask_stream(prompt)