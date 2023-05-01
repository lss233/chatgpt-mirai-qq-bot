import time
from enum import Enum
from typing import Generator, Optional, Any

import asyncio
from loguru import logger

from accounts import AccountInfoBaseModel, account_manager
from poe import Client as PoeClient

from adapter.botservice import BotAdapter


class PoeCookieAuth(AccountInfoBaseModel):
    p_b: str
    """登陆 poe.com 后 Cookie 中 p_b 的值"""

    _client: Optional[PoeClient] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client = PoeClient(self.p_b)

    def get_client(self) -> PoeClient:
        return self._client

    async def check_alive(self) -> bool:
        return self._client.ws_connected


class BotType(Enum):
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
                for bot in BotType
                if str(bot.name).lower() == tmp_name
                   or str(bot.value).lower() == tmp_name
                   or f"poe-{str(bot.name).lower()}" == tmp_name
            ),
            None,
        )


class PoeClientWrapper:
    def __init__(self, client_id: int, client: PoeClient, p_b: str):
        self.client_id = client_id
        self.client = client
        self.p_b = p_b
        self.last_ask_time = None


class PoeAdapter(BotAdapter):

    account: PoeCookieAuth

    def __init__(self, session_id: str = "unknown", bot_type: BotType = None):
        """获取内部队列"""
        super().__init__(session_id)
        self.session_id = session_id
        self.bot_type = bot_type or BotType.ChatGPT
        self.account = account_manager.pick("poe-token")
        self.account.get_client().create_bot()

    async def ask(self, msg: str) -> Generator[str, None, None]:
        """向 AI 发送消息"""
        # 覆盖 PoeClient 内部的锁逻辑
        while None in self.account.client.active_messages.values():
            await asyncio.sleep(0.01)
        for final_resp in self.account.client.send_message(chatbot=self.bot_type.value, message=msg):
            yield final_resp["text"]

    async def rollback(self):
        """回滚对话"""
        self.account.client.purge_conversation(self.bot_type.value, 2)

    async def on_destoryed(self):
        """当会话被重置时，此函数被调用"""
        self.account.client.send_chat_break(self.bot_type.value)
