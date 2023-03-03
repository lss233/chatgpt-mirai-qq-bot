from graia.ariadne.message.element import Image

from utils.text_to_img import to_image


class Renderer:
    context = {}
    async def parse(self, msg: str): ...
    async def result(self): ...

class FullTextRenderer(Renderer):
    msg: str

    async def render(self, msg: str) -> None:
        self.msg = msg
        return None

    async def result(self) -> str:
        return self.msg
    async def __aenter__(self) -> None:
        self.msg = ''

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.msg = None

class MarkdownImageRenderer(Renderer):
    msg: str

    async def render(self, msg: str) -> None:
        self.msg = msg
        return None

    async def result(self) -> Image:
        return await to_image(self.msg)
    async def __aenter__(self) -> None:
        self.msg = ''

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.msg = None