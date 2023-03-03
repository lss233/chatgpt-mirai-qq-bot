import sys, os


sys.path.append(os.getcwd())
from middlewares.middleware import ValueMiddleware

from middlewares.ratelimit import MiddlewareRatelimit

middlewares = [MiddlewareRatelimit(), ValueMiddleware()]

def final_call(session_id, source, target, message):
    print(message)

session_id  = 1
source = 2
target = 3
message = "test"
next = final_call


def wrapper(n, m):
    def call(session_id, source, target, message):
        m.handle_request(session_id, source, target, message, n)
    return call

for m in middlewares:
    next = wrapper(next, m)

next(session_id, source, target, message)