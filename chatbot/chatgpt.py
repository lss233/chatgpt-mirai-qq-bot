import datetime
import os
import sys

sys.path.append(os.getcwd())

import asyncio
from typing import Union
from revChatGPT.V1 import Chatbot as V1Chatbot
from revChatGPT.Unofficial import Chatbot as BrowserChatbot
from config import OpenAIAuthBase


class ChatGPTBrowserChatbot(asyncio.Lock):
    id = 0

    account: OpenAIAuthBase

    bot: Union[V1Chatbot, BrowserChatbot]

    mode: str

    queue_size: int = 0

    unused_conversations_pools = {}

    accessed_at = []
    """访问时间，仅保存一小时以内的时间"""

    last_rate_limited = None
    """上一次遇到限流的时间"""

    def __init__(self, bot, mode):
        self.bot = bot
        self.mode = mode
        super().__init__()

    def update_accessed_at(self):
        """更新最后一次请求的时间，用于流量统计"""
        current_time = datetime.datetime.now()
        self.accessed_at.append(current_time)
        self.refresh_accessed_at()

    def refresh_accessed_at(self):
        # 删除栈顶过期的信息
        current_time = datetime.datetime.now()
        while len(self.accessed_at) > 0 and current_time - self.accessed_at[0] > datetime.timedelta(hours=1):
            self.accessed_at.pop(0)

    def delete_conversation(self, conversation_id):
        self.bot.delete_conversation(conversation_id)

    def ask(self, prompt, conversation_id=None, parent_id=None):
        """向 ChatGPT 发送提问"""
        self.bot.conversation_id = None
        self.bot.parent_id = None
        resp = self.bot.ask(prompt=prompt, conversation_id=conversation_id, parent_id=parent_id)
        if self.mode == 'proxy' or self.mode == 'browserless':
            for r in resp:
                yield r
            self.update_accessed_at()
        else:
            yield resp
            self.update_accessed_at()

    def __str__(self) -> str:
        return self.bot.__str__()

    async def __aenter__(self) -> None:
        self.queue_size = self.queue_size + 1
        return await super().__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.queue_size = self.queue_size - 1
        return await super().__aexit__(exc_type, exc, tb)
