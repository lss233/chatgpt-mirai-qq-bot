# encoding:utf-8
# OpenAI 对话模型API (可用)
import ctypes
import tempfile
from typing import Generator

import aiohttp
# import openai
from PIL import Image
from loguru import logger

from adapter.botservice import BotAdapter
# from config import SDwebUI
from constants import botManager
from adapter.sdwebui.ChatGPT_SDwebUI import text_to_img, img_to_img
import httpx


class SDwebUIAdapter(BotAdapter):

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.account = botManager.pick('sdwebui-api')

    async def rollback(self):
        return True

    async def on_reset(self):
        pass

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        pass

    async def image_creation(self, prompt: str):
        logger.debug(f"[SDwebUI Image] Prompt: {prompt}")
        image_url = text_to_img(prompt)
        logger.debug(f"[Text to Image] Response: {image_url}")
        return image_url

    async def image_variation(self, src_img: Image, prompt: str):
        f = tempfile.mktemp(suffix='.png', dir='D:/TG图生图/')
        src_img.save(f, format='PNG')
        image = open(f, 'rb')
        image_url = img_to_img(image, prompt)
        logger.debug(f"[Image to Image] Response: {image_url}")
        return image_url

    async def __download_image(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=self.api_info.proxy) as resp:
                if resp.status == 200:
                    return await resp.read()
