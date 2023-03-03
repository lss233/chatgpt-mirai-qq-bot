from middlewares.middleware import Middleware


class MiddlewareRatelimit(Middleware):
    def __init__(self): ...

    def handle_request(self, session_id, source, target, message, next):
        print("MiddlewareRatelimit", message)
        # if True:
        #     # Blocked
        #     return
        # Pass it along
        next(session_id, source, target, message)
