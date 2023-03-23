# encoding:utf-8
# OpenAI 对话模型API (可用)
import ctypes
import tempfile
from typing import Generator

import aiohttp
import openai
from PIL import Image
from loguru import logger

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager

hashu = lambda word: ctypes.c_uint64(hash(word)).value


class OpenAIAPIAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None
    """API Key"""

    hashed_user_id: str

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.hashed_user_id = "user-" + hashu(self.session_id).to_bytes(8, "big").hex()
        self.api_info = botManager.pick('openai-api')
        openai.proxy = self.api_info.proxy
        super().__init__()

    async def rollback(self):
        return True

    async def on_reset(self):
        self.api_info = botManager.pick('openai-api')

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        yield None

    async def preset_ask(self, role: str, text: str):
        yield None

    async def image_creation(self, prompt: str):
        logger.debug(f"[OpenAI Image] Prompt: {prompt}")
        response = await openai.Image.acreate(
            api_key=self.api_info.api_key,
            prompt=prompt,  # 图片描述
            n=1,  # 每次生成图片的数量
            size="512x512",  # 图片大小,可选有 256x256, 512x512, 1024x1024
            user=self.hashed_user_id
        )
        image_url = response['data'][0]['url']
        logger.debug(f"[OpenAI Image] Response: {image_url}")
        return await self.__download_image(image_url)

    async def image_variation(self, src_img: Image):
        f = tempfile.mktemp(suffix='.png')
        src_img.save(f, format='PNG')
        response = await openai.Image.acreate_variation(
            api_key=self.api_info.api_key,
            image=open(f, 'rb'),
            n=1,
            size="512x512",
            user=self.hashed_user_id
        )
        image_url = response['data'][0]['url']
        logger.debug(f"[OpenAI Image] Response: {image_url}")
        return await self.__download_image(image_url)

    async def __download_image(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=self.api_info.proxy) as resp:
                if resp.status == 200:
                    return await resp.read()
