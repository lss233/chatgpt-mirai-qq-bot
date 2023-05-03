from framework.renderer import Renderer
from constants import config

from typing import Optional, Any
import time

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain


class BufferedContentMerger(Renderer):
    last_arrived = None
    hold = None

    def __init__(self, parent: Renderer):
        self.parent = parent

    async def __aenter__(self) -> "BufferedContentMerger":
        self.hold = []
        self.last_arrived = time.time()
        await self.parent.__aenter__()
        return self

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.hold = None
        await self.parent.__aexit__(exc_type, exc, tb)

    async def render(self, msg: str) -> Optional[Any]:
        current_time = time.time()
        time_delta = current_time - self.last_arrived

        rendered = await self.parent.render(msg)
        if not rendered:
            return None
        if not self.hold:
            self.hold = []
        self.hold.append(Plain(rendered + '\n'))
        if time_delta < config.response.buffer_delay:
            return None
        elif self.hold:
            self.last_arrived = current_time
            rendered = MessageChain(self.hold)
            self.hold = []
            return rendered
        return None

    async def result(self) -> Optional[Any]:
        result = MessageChain([])
        if self.hold:
            result = result + MessageChain(self.hold)
        if parent := await self.parent.result():
            result = result + parent
        return result if len(result) > 0 else None


class LengthContentMerger(Renderer):
    hold = None

    def __init__(self, parent: Renderer):
        self.parent = parent

    async def __aenter__(self) -> "LengthContentMerger":
        self.hold = MessageChain([])
        self.last_arrived = time.time()
        await self.parent.__aenter__()
        return self

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.hold = None
        await self.parent.__aexit__(exc_type, exc, tb)

    async def render(self, msg: str) -> Optional[Any]:
        rendered = await self.parent.render(msg)
        if not rendered:
            return None
        if len(str(self.hold + rendered + '\n')) > 1500:
            chain = MessageChain(self.hold)
            self.hold = MessageChain([Plain(rendered + '\n')])
            return chain
        else:
            self.hold = self.hold + Plain(rendered + '\n')

    async def result(self) -> Optional[Any]:
        result = MessageChain([])
        if self.hold:
            result = result + MessageChain(self.hold)
        if parent := await self.parent.result():
            result = result + parent
        return result if len(result) > 0 else None
