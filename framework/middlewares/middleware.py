from typing import Callable

from framework.request import Response, Request


class Middleware:
    async def handle_request(self, request: Request, response: Response, _next: Callable):
        pass

    async def handle_respond(self, request: Request, response: Response, _next: Callable):
        pass

    async def on_respond(self, *args, **kwargs):
        pass

    async def handle_respond_completed(self, *args, **kwargs):
        pass
