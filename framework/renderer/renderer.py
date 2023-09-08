import re

from framework.renderer import Renderer
from framework.utils.asyncutils import evaluate_array
from framework.utils.text_to_img import to_image

from typing import Optional

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain


class PlainTextRenderer(Renderer):
    def __init__(self, parent: Renderer):
        self.parent = parent

    async def __aenter__(self) -> None:
        await self.parent.__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        await self.parent.__aexit__(exc_type, exc, tb)

    async def parse(self, groups: Optional[MessageChain]) -> Optional[MessageChain]:
        if not groups:
            return None
        everything = ''
        # 合并同类项
        for rendered in groups:
            if not str(rendered).strip():
                continue
            everything = everything + str(rendered)
        return MessageChain([Plain(everything)]) if everything else None

    async def render(self, msg: str) -> Optional[MessageChain]:
        return await self.parse(await self.parent.render(msg))

    async def result(self) -> Optional[MessageChain]:
        return await self.parse(await self.parent.result())


class MarkdownImageRenderer(Renderer):
    def __init__(self, parent: Renderer):
        self.parent = parent

    async def __aenter__(self) -> None:
        await self.parent.__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        await self.parent.__aexit__(exc_type, exc, tb)

    async def parse(self, groups: Optional[MessageChain]) -> Optional[MessageChain]:
        if not groups:
            return None
        everything = ''
        # 合并同类项
        for rendered in groups:
            if not str(rendered).strip():
                continue
            everything = everything + str(rendered) + '  \n'
        return MessageChain([await to_image(everything)]) if everything else None

    async def render(self, msg: str) -> Optional[MessageChain]:
        return await self.parse(await self.parent.render(msg))

    async def result(self) -> Optional[MessageChain]:
        return await self.parse(await self.parent.result())


class MixedContentMessageChainRenderer(Renderer):

    def __init__(self, parent: Renderer):
        self.parent = parent

    async def __aenter__(self) -> None:
        await self.parent.__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        await self.parent.__aexit__(exc_type, exc, tb)

    def is_rich_content(self, input_str: str):
        # Regular expressions to search for Markdown or LaTeX patterns
        markdown_pattern = r"(\*\*|__|\*|_|\[|\]|\(|\)|#|\+|\-|`|~|>|!)\w*(\*\*|__|\*|_|\[|\]\(|\(|\)|#|\+|\-|`|~|>|!)"
        latex_pattern = r"\$(.*?)\$"

        # Search for Markdown or LaTeX patterns in the input string
        return bool(
            re.search(markdown_pattern, input_str)
            or re.search(latex_pattern, input_str)
        )

    async def parse(self, groups: Optional[MessageChain]) -> Optional[MessageChain]:
        if not groups:
            return None
        holds = []
        rich_blocks = ''
        plain_blocks = ''
        # 合并同类项
        for rendered in groups:
            if not str(rendered).strip():
                continue
            if self.is_rich_content(str(rendered)):
                if plain_blocks.strip():
                    holds.append(Plain(plain_blocks.strip()))
                    plain_blocks = ''
                rich_blocks = rich_blocks + str(rendered) + '  \n'
            else:
                if rich_blocks.strip():
                    holds.append(await to_image(rich_blocks.strip()))
                    rich_blocks = ''
                plain_blocks = plain_blocks + str(rendered)
        # 判断最后一项，把剩余的东西丢进去
        if rich_blocks.strip():
            holds.append(await to_image(rich_blocks))
        if plain_blocks.strip():
            holds.append(Plain(plain_blocks))
        await evaluate_array(holds)
        return MessageChain(holds) if holds else None

    async def render(self, msg: str) -> Optional[MessageChain]:
        return await self.parse(await self.parent.render(msg))

    async def result(self) -> Optional[MessageChain]:
        return await self.parse(await self.parent.result())
