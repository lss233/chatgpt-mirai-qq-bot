from typing import Callable, Dict

from loguru import logger

from constants import config
from framework.conversation import ConversationHandler
from framework.middlewares.middleware import Middleware
from framework.request import Response, Request
from framework.utils import QueueInfo


class MiddlewareConcurrentLock(Middleware):
    ctx: Dict[str, QueueInfo] = dict()

    def __init__(self):
        ...

    async def handle_request(self, request: Request, response: Response, _next: Callable):
        handler = await ConversationHandler.get_handler(request.session_id)

        if request.session_id not in self.ctx:
            self.ctx[request.session_id] = QueueInfo()
        queue_info = self.ctx[request.session_id]
        selected_ctx = request.conversation_context if request.conversation_context else handler.current_conversation
        if internal_queue := selected_ctx.llm_adapter.get_queue_info():
            logger.trace("[Concurrent] 使用 Adapter 内部的 Queue")
            # 如果 Adapter 内部实现了 Queue，则用在用他们的之前先把中间件的队先排完
            logger.debug(f"[Concurrent] 排队中，前面还有 {queue_info.size} 个人！")
            async with queue_info:
                queue_info = internal_queue
        # 队列满时拒绝新的消息
        if 0 < config.response.max_queue_size < queue_info.size:
            logger.debug("[Concurrent] 队列已满，拒绝服务！")
            await response.send(text=config.response.queue_full)
            return
        else:
            # 提示用户：请求已加入队列
            if queue_info.size > config.response.queued_notice_size:
                await response.send(text=config.response.queued_notice.format(queue_size=queue_info.size))
        # 在队列中执行
        logger.trace(f"[Concurrent] 排队中，前面还有 {queue_info.size} 个人！")
        async with queue_info:
            logger.trace("[Concurrent] 排到了！")
            await _next(request, response)
