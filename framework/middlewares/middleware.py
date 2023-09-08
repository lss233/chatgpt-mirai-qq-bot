from typing import Callable

from framework.request import Response, Request


class Middleware:
    async def handle_request(self, request: Request, response: Response, _next: Callable):
        return await _next(request, response)

    async def handle_respond(self, request: Request, response: Response, _next: Callable):
        return await _next(request, response)

    async def on_respond(self, *args, **kwargs):
        pass

    async def handle_respond_completed(self, *args, **kwargs):
        pass
