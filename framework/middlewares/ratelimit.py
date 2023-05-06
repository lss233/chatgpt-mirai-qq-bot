import time
from typing import Callable, Optional

from constants import config
from framework.conversation import ConversationContext
from framework.request import Request, Response
from manager.ratelimit import RateLimitManager
from framework.middlewares.middleware import Middleware

manager = RateLimitManager()


class MiddlewareRatelimit(Middleware):
    def __init__(self):
        ...

    async def handle_request(self, request: Request, response: Response, _next: Callable):
        _id = request.session_id.split('-', 1)[1] if '-' in request.session_id else request.session_id
        rate_usage = manager.check_exceed('好友' if request.session_id.startswith("friend-") else '群组', _id)
        if rate_usage >= 1:
            await response.send(text=config.ratelimit.exceed)
            return
        await _next(request, response)

    async def handle_respond_completed(self, request: Request, response: Response):
        key = '好友' if request.session_id.startswith("friend-") else '群组'
        msg_id = request.session_id.split('-', 1)[1]
        manager.increment_usage(key, msg_id)
        rate_usage = manager.check_exceed(key, msg_id)
        if rate_usage >= config.ratelimit.warning_rate:
            limit = manager.get_limit(key, msg_id)
            usage = manager.get_usage(key, msg_id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await response.send(config.ratelimit.warning_msg.format(usage=usage['count'],
                                                        limit=limit['rate'],
                                                        current_time=current_time))
