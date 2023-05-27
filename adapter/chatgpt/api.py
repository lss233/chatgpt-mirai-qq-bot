import ctypes
import os
from typing import Generator
import openai
from loguru import logger
from revChatGPT.V3 import Chatbot as OpenAIChatbot

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager, config

hashu = lambda word: ctypes.c_uint64(hash(word)).value


class ChatGPTAPIAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None
    """API Key"""

    bot: OpenAIChatbot = None
    """实例"""

    hashed_user_id: str

    def __init__(self, session_id: str = "unknown"):
        self.__conversation_keep_from = 0
        self.session_id = session_id
        self.hashed_user_id = "user-" + hashu("session_id").to_bytes(8, "big").hex()
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(
            api_key=self.api_info.api_key,
            proxy=self.api_info.proxy,
            presence_penalty=config.openai.gpt3_params.presence_penalty,
            frequency_penalty=config.openai.gpt3_params.frequency_penalty,
            top_p=config.openai.gpt3_params.top_p,
            temperature=config.openai.gpt3_params.temperature,
            max_tokens=config.openai.gpt3_params.max_tokens,
        )
        self.conversation_id = None
        self.parent_id = None
        super().__init__()
        self.bot.conversation[self.session_id] = []
        self.current_model = self.api_info.model or "gpt-3.5-turbo"
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

    async def on_reset(self):
        self.api_info = botManager.pick('openai-api')
        self.bot.api_key = self.api_info.api_key
        self.bot.proxy = self.api_info.proxy
        self.bot.conversation[self.session_id] = []
        self.__conversation_keep_from = 0

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.api_info = botManager.pick('openai-api')
        self.bot.api_key = self.api_info.api_key
        self.bot.proxy = self.api_info.proxy
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

        while self.bot.max_tokens - self.bot.get_token_count(self.session_id) < config.openai.gpt3_params.min_tokens and \
                len(self.bot.conversation[self.session_id]) > self.__conversation_keep_from:
            self.bot.conversation[self.session_id].pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(self.bot.get_token_count(self.session_id))}"
            )

        os.environ['API_URL'] = f'{openai.api_base}/chat/completions'
        full_response = ''
        async for resp in self.bot.ask_stream_async(prompt=prompt, role=self.hashed_user_id, convo_id=self.session_id):
            full_response += resp
            yield full_response
        logger.debug(f"[ChatGPT-API:{self.bot.engine}] 响应：{full_response}")
        logger.debug(f"使用 token 数：{str(self.bot.get_token_count(self.session_id))}")

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role in {'assistant', 'chatgpt'}:
            logger.debug(f"[预设] 响应：{text}")
            yield text
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        if self.session_id not in self.bot.conversation:
            self.bot.conversation[self.session_id] = []
            self.__conversation_keep_from = 0
        self.bot.conversation[self.session_id].append({"role": role, "content": text})
        self.__conversation_keep_from = len(self.bot.conversation[self.session_id])
