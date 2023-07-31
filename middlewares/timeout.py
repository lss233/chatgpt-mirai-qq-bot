from typing import Callable, Dict, Optional

import asyncio
from conversation import ConversationContext
from loguru import logger

from constants import config
from middlewares.middleware import Middleware


class MiddlewareTimeout(Middleware):
    timeout_task: Dict[str, asyncio.Task] = dict()
    request_task: Dict[str, asyncio.Task] = dict()
    ctx: Dict[str, ConversationContext] = dict()

    def __init__(self):
        ...

    async def handle_request(self, session_id: str, prompt: str, respond: Callable,
                             conversation_context: Optional[ConversationContext], action: Callable):
        if session_id in self.timeout_task:
            self.timeout_task[session_id].cancel()
        self.timeout_task[session_id] = asyncio.create_task(self.create_timeout_task(respond, session_id))
        coro_task = asyncio.create_task(action(session_id, prompt, conversation_context, respond))
        self.request_task[session_id] = coro_task
        try:
            await asyncio.wait_for(coro_task, config.response.max_timeout)
            if session_id in self.timeout_task and not (
                    self.timeout_task[session_id].cancel() or self.timeout_task[session_id].done()
            ):
                self.timeout_task[session_id].cancel()
                del self.timeout_task[session_id]
        except asyncio.TimeoutError:
            await respond(config.response.cancel_wait_too_long)
        except Exception as e:
            logger.error(f"发生错误: {e}")
            if session_id in self.timeout_task:
                self.timeout_task[session_id].cancel()
                del self.timeout_task[session_id]
            raise e

    async def on_respond(self, session_id: str, prompt: str, rendered: str):
        if rendered and session_id in self.timeout_task:
            self.timeout_task[session_id].cancel()
            del self.timeout_task[session_id]
            logger.debug("[Timeout] 取消计时……")

    async def handle_respond(self, session_id: str, prompt: str, rendered: str, respond: Callable, action: Callable):
        if rendered and session_id in self.timeout_task:
            self.timeout_task[session_id].cancel()
            del self.timeout_task[session_id]
            logger.debug("[Timeout] 取消计时……")

        await action(session_id, prompt, rendered, respond)

        if not self.request_task[session_id].done():
            # Create the task again
            self.timeout_task[session_id] = asyncio.create_task(self.create_timeout_task(respond, session_id))

    async def create_timeout_task(self, respond, session_id):
        logger.debug("[Timeout] 开始计时……")
        await asyncio.sleep(config.response.timeout)
        respond_msg = await respond(config.response.timeout_format)
        logger.debug("[Timeout] 等待过久，发送提示")
        await asyncio.sleep(90)
        if ctx := self.ctx[session_id]:
            await ctx.delete_message(respond_msg)
