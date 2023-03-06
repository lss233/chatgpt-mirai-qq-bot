import datetime
from typing import Generator, Union

import asyncio
import janus
from loguru import logger

from adapter.botservice import BotAdapter
from chatbot.chatgpt import ChatGPTBrowserChatbot

from constants import config, botManager
from revChatGPT.V1 import Error as V1Error

from exceptions import BotRatelimitException, ConcurrentMessageException


class ChatGPTWebAdapter(BotAdapter):
    conversation_id: str
    """会话 ID"""

    parent_id: str
    """上文 ID"""

    conversation_id_prev_queue = []
    parent_id_prev_queue = []

    bot: ChatGPTBrowserChatbot = None
    """实例"""

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.bot = botManager.pick('chatgpt-web')
        self.conversation_id = None
        self.parent_id = None
        super().__init__()

    async def rollback(self):
        if len(self.parent_id_prev_queue) > 0:
            self.parent_id = self.parent_id_prev_queue.pop()
            return True
        else:
            return False

    async def on_reset(self):
        if self.bot.account.auto_remove_old_conversations:
            if self.conversation_id is not None:
                self.bot.delete_conversation(self.conversation_id)
        self.conversation_id = None
        self.parent_id = None
        self.bot = botManager.pick('chatgpt-web')

    def ask_sync(self, sync_q, prompt):
        try:
            for resp in self.bot.ask(prompt, self.conversation_id, self.parent_id):
                sync_q.put(resp)
            sync_q.put(None)
        except Exception as e:
            sync_q.put(e)
        sync_q.join()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        # 队列满时拒绝新的消息
        if 0 < config.response.max_queue_size < self.bot.queue_size:
            yield config.response.queue_full
            return
        else:
            # 提示用户：请求已加入队列
            if self.bot.queue_size > config.response.queued_notice_size:
                yield config.response.queued_notice.format(queue_size=self.bot.queue_size)
        async with self.bot:
            try:
                queue: janus.Queue[Union[str, Exception, None]] = janus.Queue()
                loop = asyncio.get_running_loop()
                future = loop.run_in_executor(None, self.ask_sync, queue.sync_q, prompt)
                last_response = None
                while not queue.async_q.closed:
                    resp = await queue.async_q.get()
                    queue.async_q.task_done()
                    if isinstance(resp, Exception):
                        # 出现了错误
                        raise resp
                    elif resp is None:
                        # 发完了
                        break
                    last_response = resp
                    if self.conversation_id:
                        self.conversation_id_prev_queue.append(self.conversation_id)
                    if self.parent_id:
                        self.conversation_id_prev_queue.append(self.parent_id)

                    # 初始化会话 ID
                    if not self.conversation_id:
                        self.conversation_id = resp["conversation_id"]
                        if self.bot.account.title_pattern:
                            self.bot.rename_conversation(self.conversation_id, self.bot.account.title_pattern
                                                         .format(session_id=self.session_id))

                    # 确保是当前的会话，才更新 parent_id
                    if self.conversation_id == resp["conversation_id"]:
                        self.parent_id = resp["parent_id"]
                    yield resp["message"]

                await future
                queue.close()
                await queue.wait_closed()
                if last_response:
                    logger.debug(f"[ChatGPT-Web] {last_response['conversation_id']} - {last_response['message']}")
            except AttributeError as e:
                if str(e).startswith("'str' object has no attribute 'get'"):
                    yield "出现故障，请发送”{reset}“重新开始！".format(reset=config.trigger.reset_command)
            except V1Error as e:
                if e.code == 2:
                    current_time = datetime.datetime.now()
                    self.bot.refresh_accessed_at()
                    logger.debug("[ChatGPT-Web] accessed at: " + self.bot.accessed_at)
                    first_accessed_at = self.bot.accessed_at[0] if len(self.bot.accessed_at) > 0 \
                        else current_time - datetime.timedelta(hours=1)
                    remaining = divmod(current_time - first_accessed_at, datetime.timedelta(seconds=60))
                    minute = remaining[0]
                    second = remaining[1].seconds
                    raise BotRatelimitException(f"{minute}分{second}秒")
                if e.code == 6:
                    raise ConcurrentMessageException()
                raise e

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role == 'chatgpt':
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")
            pass  # 不发送 AI 的回应，免得串台
