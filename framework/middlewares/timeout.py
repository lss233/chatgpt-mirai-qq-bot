from typing import Callable, Dict

import asyncio
from loguru import logger

from constants import config
from framework.conversation import ConversationContext
from framework.middlewares.middleware import Middleware
from framework.request import Request, Response


class MiddlewareTimeout(Middleware):
    timeout_task: Dict[str, asyncio.Task] = dict()
    request_task: Dict[str, asyncio.Task] = dict()
    ctx: Dict[str, ConversationContext] = dict()

    def __init__(self):
        ...

    async def handle_request(self, request: Request, response: Response, _next: Callable):
        if request.session_id in self.timeout_task:
            self.timeout_task[request.session_id].cancel()
        self.timeout_task[request.session_id] = asyncio.create_task(
            self.create_timeout_task(response.send, request.session_id))
        coro_task = asyncio.create_task(_next(request, response))
        self.request_task[request.session_id] = coro_task
        try:
            await asyncio.wait_for(coro_task, config.response.max_timeout)
            if request.session_id in self.timeout_task and not (
                    self.timeout_task[request.session_id].cancel() or self.timeout_task[request.session_id].done()):
                self.timeout_task[request.session_id].cancel()
                del self.timeout_task[request.session_id]
        except asyncio.TimeoutError:
            await response.send(text=config.response.cancel_wait_too_long)

    async def handle_respond(self, request: Request, response: Response, _next: Callable):
        if response.has_content and request.session_id in self.timeout_task:
            self.timeout_task[request.session_id].cancel()
            del self.timeout_task[request.session_id]
            logger.debug("[Timeout] 取消计时……")

        await _next(request, response)

        if request.session_id in self.request_task and not self.request_task[request.session_id].done(
        ):
            # Create the task again
            self.timeout_task[request.session_id] = asyncio.create_task(
                self.create_timeout_task(response.send, request.session_id))

    async def create_timeout_task(self, respond, session_id):
        logger.debug("[Timeout] 开始计时……")
        await asyncio.sleep(config.response.timeout)
        respond_msg = await respond(text=config.response.timeout_format)
        logger.debug("[Timeout] 等待过久，发送提示")
        await asyncio.sleep(90)
        if ctx := self.ctx[session_id]:
            await ctx.delete_message(respond_msg)
