import ctypes
import os
from typing import Generator

import httpx
import openai
import tempfile
from io import BytesIO
from typing import List

import aiohttp
from graia.ariadne.message.element import Image as GraiaImage
from PIL import Image
from loguru import logger
from revChatGPT.V3 import Chatbot as OpenAIChatbot
from revChatGPT.typings import APIConnectionError

import constants
from config import OpenAIGPT3Params
from framework.accounts import account_manager
from framework.exceptions import LlmRequestTimeoutException, LlmRequestFailedException
from framework.llm.openai.models import OpenAIAPIKeyAuth
from framework.llm.llm import Llm
from framework.drawing import DrawAI


class ChatGPTAPIAdapter(Llm, DrawAI):
    api_info: OpenAIAPIKeyAuth = None
    """API Key"""

    bot: OpenAIChatbot = None
    """实例"""

    hashed_user_id: str

    def __init__(self, session_id: str = "unknown", params=OpenAIGPT3Params()):
        self.__conversation_keep_from = 0
        self.session_id = session_id
        self.hashed_user_id = "user-" + ctypes.c_uint64(hash(self.session_id)).value.to_bytes(8, "big").hex()
        self.api_info = account_manager.pick('openai-api')
        self.params = params
        self.bot = OpenAIChatbot(
            api_key=self.api_info.api_key,
            proxy=constants.proxy,
            presence_penalty=params.presence_penalty,
            frequency_penalty=params.frequency_penalty,
            top_p=params.top_p,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
        )
        self.conversation_id = None
        self.parent_id = None
        super().__init__()
        self.bot.conversation[self.session_id] = []
        self.current_model = "gpt-3.5-turbo"
        self.supported_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0301",
            "gpt-4",
            "gpt-4-0314",
            "gpt-4-32k",
            "gpt-4-32k-0314",
        ]

    async def switch_model(self, model_name):
        self.current_model = model_name
        self.bot.engine = self.current_model

    async def rollback(self):
        if len(self.bot.conversation[self.session_id]) <= 0:
            return False
        self.bot.rollback(convo_id=self.session_id, n=2)
        return True

    async def on_destoryed(self):
        """重置会话"""
        ...

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.api_info = account_manager.pick('openai-api')
        self.bot.api_key = self.api_info.api_key
        self.bot.proxy = constants.proxy
        self.bot.session.proxies.update(
            {
                "http": self.bot.proxy,
                "https": self.bot.proxy,
            },
        )

        if self.session_id not in self.bot.conversation:
            self.bot.conversation[self.session_id] = [
                {"role": "system", "content": self.bot.system_prompt}
            ]
            self.__conversation_keep_from = 1

        while self.bot.max_tokens - self.bot.get_token_count(self.session_id) < self.params.min_tokens and \
                len(self.bot.conversation[self.session_id]) > self.__conversation_keep_from:
            self.bot.conversation[self.session_id].pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(self.bot.get_token_count(self.session_id))}"
            )

        os.environ['API_URL'] = f'{openai.api_base}/chat/completions'
        full_response = ''
        try:
            async for resp in self.bot.ask_stream_async(prompt=prompt, role=self.hashed_user_id, convo_id=self.session_id):
                full_response += resp
                yield full_response
            logger.debug(f"[ChatGPT-API:{self.bot.engine}] 响应：{full_response}")
            logger.debug(f"使用 token 数：{str(self.bot.get_token_count(self.session_id))}")
        except httpx.TimeoutException as e:
            raise LlmRequestTimeoutException("chatgpt-api") from e
        except APIConnectionError as e:
            raise LlmRequestFailedException("chatgpt-api") from e

    async def preset_ask(self, role: str, prompt: str):
        if role.endswith('bot') or role in {'assistant', 'chatgpt'}:
            logger.debug(f"[预设] 响应：{prompt}")
            yield prompt
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        if self.session_id not in self.bot.conversation:
            self.bot.conversation[self.session_id] = []
            self.__conversation_keep_from = 0
        self.bot.conversation[self.session_id].append({"role": role, "content": prompt})
        self.__conversation_keep_from = len(self.bot.conversation[self.session_id])

    async def text_to_img(self, prompt: str):
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
        return [await self.__download_image(image_url)]

    async def img_to_img(self, init_images: List[GraiaImage], prompt=''):
        f = tempfile.mktemp(suffix='.png')
        raw_bytes = BytesIO(await init_images[0].get_bytes())
        raw_image = Image.open(raw_bytes)

        raw_image.save(f, format='PNG')
        response = await openai.Image.acreate_variation(
            api_key=self.api_info.api_key,
            image=open(f, 'rb'),
            n=1,
            size="512x512",
            user=self.hashed_user_id
        )
        image_url = response['data'][0]['url']
        logger.debug(f"[OpenAI Image] Response: {image_url}")
        return [await self.__download_image(image_url)]

    async def __download_image(self, url) -> GraiaImage:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=constants.proxy) as resp:
                if resp.status == 200:
                    return GraiaImage(data_bytes=await resp.read())

    @classmethod
    def register(cls):
        account_manager.register_type("openai-api", OpenAIAPIKeyAuth)
