import datetime
import asyncio
from revChatGPT.V1 import AsyncChatbot as V1Chatbot
from config import OpenAIAuthBase
from utils import QueueInfo


class ChatGPTBrowserChatbot(asyncio.Lock):
    id = 0

    account: OpenAIAuthBase

    bot: V1Chatbot

    mode: str

    queue: QueueInfo

    unused_conversations_pools = {}

    accessed_at = []
    """访问时间，仅保存一小时以内的时间"""

    last_rate_limited = None
    """上一次遇到限流的时间"""

    def __init__(self, bot, mode):
        self.bot = bot
        self.mode = mode
        self.queue = QueueInfo()
        super().__init__()

    def update_accessed_at(self):
        """更新最后一次请求的时间，用于流量统计"""
        current_time = datetime.datetime.now()
        self.accessed_at.append(current_time)
        self.refresh_accessed_at()

    async def rename_conversation(self, conversation_id: str, title: str):
        await self.bot.change_title(conversation_id, title)

    def refresh_accessed_at(self):
        # 删除栈顶过期的信息
        current_time = datetime.datetime.now()
        while len(self.accessed_at) > 0 and current_time - self.accessed_at[0] > datetime.timedelta(hours=1):
            self.accessed_at.pop(0)
        if len(self.accessed_at) == 0:
            self.accessed_at.append(current_time)

    async def delete_conversation(self, conversation_id):
        await self.bot.delete_conversation(conversation_id)

    async def ask(self, prompt, conversation_id=None, parent_id=None, model=''):
        """向 ChatGPT 发送提问"""
        # self.queue 已交给 MiddlewareConcurrentLock 处理，此处不处理
        self.bot.conversation_id = conversation_id
        self.bot.parent_id = parent_id
        self.bot.config['model'] = model
        async for r in self.bot.ask(prompt=prompt, conversation_id=conversation_id, parent_id=parent_id):
            yield r
        self.update_accessed_at()

    def __str__(self) -> str:
        return self.bot.__str__()
