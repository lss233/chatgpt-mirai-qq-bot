
class Middleware:
    def handle_request(self, session_id, source, target, message, next): ...
class ValueMiddleware(Middleware):
    def handle_request(self, session_id, source, target, message, next):
        print(1)
        next(session_id, source, target, message)