import time
from typing import Union, Callable, Optional

from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group

from constants import config
from conversation import ConversationContext
from manager.ratelimit import RateLimitManager
from middlewares.middleware import Middleware

manager = RateLimitManager()


class MiddlewareRatelimit(Middleware):
    def __init__(self):
        ...

    async def handle_request(self, session_id: str, prompt: str, respond: Callable,
                             conversation_context: Optional[ConversationContext], action: Callable):
        rate_usage = manager.check_exceed('好友' if session_id.startswith("friend-") else '群组', session_id)
        if rate_usage >= 1:
            await respond(config.ratelimit.exceed)
            return
        await action(session_id, prompt, conversation_context, respond)

    async def handle_respond_completed(self, session_id: str, prompt: str, respond: Callable):
        key = '好友' if session_id.startswith("friend-") else '群组'
        manager.increment_usage(key, session_id)
        rate_usage = manager.check_exceed(key, session_id)
        if rate_usage >= config.ratelimit.warning_rate:
            limit = manager.get_limit(key, session_id)
            usage = manager.get_usage(key, session_id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await respond(config.ratelimit.warning_msg.format(usage=usage['count'],
                                                        limit=limit['rate'],
                                                        current_time=current_time))
