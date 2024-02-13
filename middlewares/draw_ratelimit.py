import time
from typing import Callable, Optional

from constants import config
from manager.ratelimit import RateLimitManager

manager = RateLimitManager()


class MiddlewareRatelimit():
    def __init__(self):
        ...


    def handle_draw_request(self, session_id: str, prompt: str):
        _id = session_id.split('-', 1)[1] if '-' in session_id and not session_id.startswith('-') and not session_id.endswith('-') else session_id
        key = '好友' if session_id.startswith("friend-") else '群组'
        rate_usage = manager.check_draw_exceed(key, _id)
        return config.ratelimit.draw_exceed if rate_usage >= 1 else "1"



    def handle_draw_respond_completed(self, session_id: str, prompt: str):
        key = '好友' if session_id.startswith("friend-") else '群组'
        msg_id = session_id.split('-', 1)[1] if '-' in session_id and not session_id.startswith('-') and not session_id.endswith('-') else session_id
        manager.increment_draw_usage(key, msg_id)
        rate_usage = manager.check_draw_exceed(key, msg_id)
        if rate_usage >= config.ratelimit.warning_rate:
            limit = manager.get_draw_limit(key, msg_id)
            usage = manager.get_draw_usage(key, msg_id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            return config.ratelimit.draw_warning_msg.format(usage=usage['count'],
                                                        limit=limit['rate'],
                                                        current_time=current_time)
        return "1"
