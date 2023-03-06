import time
from typing import Union, Callable, Dict

import asyncio
from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group
from loguru import logger

from constants import config
from middlewares.middleware import Middleware


async def create_timeout_task(respond):
    logger.debug("[Timeout] 开始计时……")
    await asyncio.sleep(config.response.timeout)
    await respond(config.response.timeout_format)
    logger.debug("[Timeout] 已超时")

class MiddlewareTimeout(Middleware):
    ctx: Dict[str, asyncio.Task] = dict()
    def __init__(self):
        ...

    async def handle_request(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             respond: Callable, action: Callable):
        if session_id in self.ctx:
            self.ctx[session_id].cancel()
        self.ctx[session_id] = asyncio.create_task(create_timeout_task(respond))

        await action(session_id, source, target, prompt, respond)
        # await asyncio.gather(
        #     action(session_id, source, target, prompt, respond), self.ctx[session_id]
        # )

    async def on_respond(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                                 rendered: str):
        if rendered and session_id in self.ctx:
            self.ctx[session_id].cancel()
            del self.ctx[session_id]
            logger.debug("[Timeout] 取消计时……")
    async def handle_respond(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             rendered: str, respond: Callable, action: Callable):
        if rendered and session_id in self.ctx:
            self.ctx[session_id].cancel()
            del self.ctx[session_id]
            logger.debug("[Timeout] 取消计时……")

        await action(session_id, source, target, prompt, rendered, respond)
