import time
from typing import Union, Callable, Dict

import asyncio
from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group
from loguru import logger

from constants import config
from middlewares.middleware import Middleware
import conversation
from utils import QueueInfo


class MiddlewareConcurrentLock(Middleware):
    ctx: Dict[str, QueueInfo] = dict()

    def __init__(self):
        ...

    async def handle_request(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             respond: Callable, conversation_context: Union[conversation.ConversationContext, None],
                             action: Callable):
        handler = await conversation.ConversationHandler.get_handler(session_id)

        if session_id not in self.ctx:
            self.ctx[session_id] = QueueInfo()
        queue_info = self.ctx[session_id]
        selected_ctx = handler.current_conversation if conversation_context is None else conversation_context
        if internal_queue := selected_ctx.adapter.get_queue_info():
            logger.debug("[Concurrent] 使用 Adapter 内部的 Queue")
            # 如果 Adapter 内部实现了 Queue，则用在用他们的之前先把中间件的队先排完
            logger.debug(f"[Concurrent] 排队中间件{queue_info}中，前面还有 {queue_info.size} 个人！")
            async with queue_info:
                queue_info = internal_queue
        # 队列满时拒绝新的消息
        if 0 < config.response.max_queue_size < queue_info.size:
            logger.debug(f"[Concurrent] 队列已满，拒绝服务！")
            await respond(config.response.queue_full)
            return
        else:
            # 提示用户：请求已加入队列
            if queue_info.size > config.response.queued_notice_size:
                await respond(config.response.queued_notice.format(queue_size=queue_info.size))
        # 在队列中执行
        logger.debug(f"[Concurrent] 排队中{queue_info}，前面还有 {queue_info.size} 个人！")
        async with queue_info:
            logger.debug(f"[Concurrent] 排到了！")
            await action(session_id, source, target, prompt, conversation_context, respond)
