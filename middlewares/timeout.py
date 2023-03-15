from typing import Callable, Dict, Optional

import asyncio
from conversation import ConversationContext
from loguru import logger

from constants import config
from middlewares.middleware import Middleware


async def create_timeout_task(respond):
    logger.debug("[Timeout] 开始计时……")
    await asyncio.sleep(config.response.timeout)
    await respond(config.response.timeout_format)
    logger.debug("[Timeout] 等待过久，发送提示")


class MiddlewareTimeout(Middleware):
    ctx: Dict[str, asyncio.Task] = dict()

    def __init__(self):
        ...

    async def handle_request(self, session_id: str, prompt: str, respond: Callable,
                             conversation_context: Optional[ConversationContext], action: Callable):
        if session_id in self.ctx:
            self.ctx[session_id].cancel()
        self.ctx[session_id] = asyncio.create_task(create_timeout_task(respond))
        try:
            await asyncio.wait_for(action(session_id, prompt, conversation_context, respond), config.response.max_timeout)
        except asyncio.TimeoutError:
            await respond(config.response.cancel_wait_too_long)

    async def on_respond(self, session_id: str, prompt: str, rendered: str):
        if rendered and session_id in self.ctx:
            self.ctx[session_id].cancel()
            del self.ctx[session_id]
            logger.debug("[Timeout] 取消计时……")

    async def handle_respond(self, session_id: str, prompt: str, rendered: str, respond: Callable, action: Callable):
        if rendered and session_id in self.ctx:
            self.ctx[session_id].cancel()
            del self.ctx[session_id]
            logger.debug("[Timeout] 取消计时……")

        await action(session_id, prompt, rendered, respond)
