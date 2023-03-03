from typing import Union, Callable

from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group


class Middleware:
    async def handle_request(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             respond: Callable, action: Callable):
        await action(session_id, source, target, prompt, respond)

    async def handle_respond(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             rendered: str, respond: Callable, action: Callable):
        await action(session_id, source, target, prompt, rendered, respond)


    async def handle_respond_completed(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                                       respond: Callable): ...
