from base64 import b64decode, b64encode

import aiohttp
from graia.ariadne.message.element import Image as GraiaImage


class ImageElement(GraiaImage):
    alt: str = None
    """图片的描述文本"""

    def __init__(self, alt: str = None, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        return f"[图: {self.alt}]" if self.alt else super().__str__()

    async def get_bytes(self) -> bytes:
        """尝试获取消息元素的 bytes, 注意, 你无法获取并不包含 url 且不包含 base64 属性的本元素的 bytes.

        Raises:
            ValueError: 你尝试获取并不包含 url 属性的本元素的 bytes.

        Returns:
            bytes: 元素原始数据
        """
        if self.base64:
            return b64decode(self.base64)
        if not self.url:
            raise ValueError("you should offer a url.")
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                data = await response.read()
                self.base64 = b64encode(data).decode("ascii")
                return data
