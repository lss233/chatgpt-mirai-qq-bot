import enum
from typing import Generator, List, Dict

import openai
from loguru import logger

from framework.accounts import account_manager
from framework.drawing import DrawAI
from framework.llm.llm import Llm
from framework.llm.microsoft.models import BingCookieAuth
from framework.utils.tokenutils import get_token_count

image_pattern = r"!\[.*\]\((.*)\)"


class ConversationStyle(enum.Enum):
    Creative = 'creative'
    Balanced = 'balanced'
    Precise = 'precise'


class BingAdapter(Llm, DrawAI):
    conversation_style: ConversationStyle = None

    account: BingCookieAuth
    messages: List[Dict[str, str]]

    def __init__(self, session_id: str = "unknown", conversation_style: ConversationStyle = ConversationStyle.Creative):
        super().__init__(session_id)
        self.account = account_manager.pick('bing')
        self.session_id = session_id
        self.conversation_style = conversation_style
        self.__conversation_keep_from = 0
        self.messages = []
        self.max_tokens = 7000

    async def rollback(self):
        self.messages = self.messages[:-2 or None]

    async def on_destoryed(self):
        ...

    async def ask(self, msg: str) -> Generator[str, None, None]:
        """向 AI 发送消息"""
        self.messages.append({"role": "user", "content": msg})
        full_chunk = []
        full_text = ''
        while self.max_tokens - get_token_count('gpt-4', self.messages) < 0 and \
            len(self.messages) > self.__conversation_keep_from:
            self.messages.pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(get_token_count('gpt-4', self.messages))}"
            )
        async for chunk in await openai.ChatCompletion.acreate(
            model=f'bing-{self.conversation_style.value}',
            messages=self.messages,
            stream=True,
            api_base="https://llm-proxy.lss233.com/bing/v1",
            api_key="sk-274a8645fd3clss233achatgptfor0botfe",
            headers=self.account.build_headers()
        ):
            logger.info(chunk.choices[0].delta)
            full_chunk.append(chunk.choices[0].delta)
            full_text = ''.join([m.get('content', '') for m in full_chunk])
            yield full_text
        logger.debug(f"[Bing-{self.conversation_style.value}] {self.session_id} - {full_text}")
        self.messages.append({"role": "assistant", "content": full_text})

    # async def __download_image(self, url) -> GraiaImage:
    #     logger.debug(f"[Bing AI] 下载图片：{url}")
    #
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url, proxy=self.bot.proxy) as resp:
    #             resp.raise_for_status()
    #             logger.debug(f"[Bing AI] 下载完成：{resp.content_type} {url}")
    #             return GraiaImage(data_bytes=await resp.read())

    @classmethod
    def register(cls):
        account_manager.register_type("bing", BingCookieAuth)

    async def preset_ask(self, role: str, prompt: str):
        if role.endswith('bot') or role in {'assistant', 'chatgpt'}:
            logger.debug(f"[预设] 响应：{prompt}")
            yield prompt
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        self.messages.append({"role": role, "content": prompt})
        self.__conversation_keep_from = len(self.messages)
