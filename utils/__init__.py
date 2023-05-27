import asyncio

from .retry import retry

class QueueInfo:
    lock: asyncio.Lock
    size: int

    def __init__(self):
        self.lock = asyncio.Lock()
        self.size = 0

    async def __aenter__(self) -> None:
        self.size = self.size + 1
        return await self.lock.__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.size = self.size - 1
        return await self.lock.__aexit__(exc_type, exc, tb)
