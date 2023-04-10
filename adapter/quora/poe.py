from enum import Enum
from typing import Generator

import asyncio

from adapter.botservice import BotAdapter
from constants import botManager


class PoeBot(Enum):
    """Poe 支持的机器人：{'capybara': 'Sage', 'beaver': 'GPT-4', 'a2_2': 'Claude+','a2': 'Claude', 'chinchilla': 'ChatGPT',
    'nutria': 'Dragonfly'} """
    Sage = "capybara"
    GPT4 = "beaver"
    Claude2 = "a2_2"
    Claude = "a2"
    ChatGPT = "chinchilla"
    Dragonfly = "nutria"

    @staticmethod
    def parse(bot_name: str):
        tmp_name = bot_name.lower()
        return next(
            (
                bot
                for bot in PoeBot
                if str(bot.name).lower() == tmp_name
                or str(bot.value).lower() == tmp_name
                or f"poe-{str(bot.name).lower()}" == tmp_name
            ),
            None,
        )


class PoeAdapter(BotAdapter):

    def __init__(self, session_id: str = "unknown", poe_bot: PoeBot = None):
        """获取内部队列"""
        super().__init__(session_id)
        self.session_id = session_id
        self.poe_bot = poe_bot or PoeBot.ChatGPT
        self.poe_client = botManager.pick("poe-web")

    async def ask(self, msg: str) -> Generator[str, None, None]:
        # sourcery skip: raise-specific-error
        """向 AI 发送消息"""
        final_resp = None
        while None in self.poe_client.active_messages.values():
            await asyncio.sleep(0.01)
        for final_resp in self.poe_client.send_message(chatbot=self.poe_bot.value, message=msg):
            yield final_resp["text"]
        if final_resp is None:
            raise Exception("Poe 在返回结果时出现了错误")
        yield final_resp["text"]

    async def rollback(self):
        """回滚对话"""
        self.poe_client.purge_conversation(self.poe_bot.value, 2)

    async def on_reset(self):
        """当会话被重置时，此函数被调用"""
        self.poe_client.send_chat_break(self.poe_bot.value)
 