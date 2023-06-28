import ctypes
import time
from typing import Generator
import openai
import json
import aiohttp
import async_timeout
from loguru import logger

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager, config
import tiktoken

hashu = lambda word: ctypes.c_uint64(hash(word)).value


class OpenAIChatbot:
    def __init__(self, api_info: OpenAIAPIKey):
        self.api_key = api_info.api_key
        self.proxy = api_info.proxy
        self.presence_penalty = config.openai.gpt3_params.presence_penalty
        self.frequency_penalty = config.openai.gpt3_params.frequency_penalty
        self.top_p = config.openai.gpt3_params.top_p
        self.temperature = config.openai.gpt3_params.temperature
        self.max_tokens = config.openai.gpt3_params.max_tokens
        self.engine = api_info.model or "gpt-3.5-turbo"
        self.timeout: float = 1800
        self.conversation: dict[str, list[dict]] = {
            "default": [
                {
                    "role": "system",
                    "content": None,
                },
            ],
        }

    async def rollback(self, session_id: str = "default", n: int = 1) -> None:
        try:
            if session_id not in self.conversation:
                raise ValueError(f"会话 ID {session_id} 不存在。")

            if n > len(self.conversation[session_id]):
                raise ValueError(f"回滚次数 {n} 超过了会话 {session_id} 的消息数量。")

            for _ in range(n):
                self.conversation[session_id].pop()

        except ValueError as ve:
            logger.error(ve)
            raise
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise

    def add_to_conversation(
            self,
            message: str,
            role: str,
            session_id: str = "default",
    ) -> None:
        self.conversation[session_id].append({"role": role, "content": message})

    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def count_tokens(self, session_id: str = "default", model: str = "gpt-3.5-turbo"):
        """Return the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return self._calc_tokens(session_id, model, encoding)

    def _calc_tokens(self, session_id: str, model: str, encoding: object):
        if model in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613"
        }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows {role/name}\n{content}\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-3.5-turbo" in model:
            logger.warning(" gpt-3.5-turbo 可能会随着时间的推移更新。这里使用最新的 gpt-3.5-turbo-0613 计算")
            return self.count_tokens(session_id, model="gpt-3.5-turbo-0613")
        elif "gpt-4" in model:
            logger.warning(" gpt-4 可能会随着时间的推移更新。这里使用最新的 gpt-4-0613 计算")
            return self.count_tokens(session_id, model="gpt-4-0613")
        else:
            logger.warning("未找到相应模型计算方法，不进行计算")
            return
        num_tokens = 0
        for message in self.conversation[session_id]:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with assistant
        return num_tokens

    def get_max_tokens(self, session_id: str, model: str) -> int:
        """Get max tokens"""
        return self.max_tokens - self.count_tokens(session_id, model)


class ChatGPTAPIAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None
    """API Key"""

    hashed_user_id: str

    def __init__(self, session_id: str = "unknown"):
        self.__conversation_keep_from = 0
        self.session_id = session_id
        self.hashed_user_id = "user-" + hashu("session_id").to_bytes(8, "big").hex()
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(self.api_info)
        self.conversation_id = None
        self.parent_id = None
        super().__init__()
        self.bot.conversation[self.session_id] = []
        self.current_model = self.api_info.model or "gpt-3.5-turbo"
        self.supported_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0301",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4",
            "gpt-4-0314",
            "gpt-4-32k",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        ]

    async def switch_model(self, model_name):
        self.current_model = model_name
        self.bot.engine = self.current_model

    async def rollback(self):
        if len(self.bot.conversation[self.session_id]) <= 0:
            return False
        await self.bot.rollback(self.session_id, n=2)
        return True

    async def on_reset(self):
        self.api_info = botManager.pick('openai-api')
        self.bot.api_key = self.api_info.api_key
        self.bot.proxy = self.api_info.proxy
        self.bot.conversation[self.session_id] = []
        self.__conversation_keep_from = 0

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.api_info = botManager.pick('openai-api')
        api_key = self.api_info.api_key
        proxy = self.api_info.proxy
        api_endpoint = config.openai.api_endpoint or "https://api.openai.com/v1/chat/completions"

        if self.session_id not in self.bot.conversation:
            self.bot.conversation[self.session_id] = [
                {"role": "system", "content": prompt}
            ]
            self.__conversation_keep_from = 1

        while self.bot.max_tokens - self.bot.count_tokens(self.session_id) < config.openai.gpt3_params.min_tokens and \
                len(self.bot.conversation[self.session_id]) > self.__conversation_keep_from:
            self.bot.conversation[self.session_id].pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(self.bot.count_tokens(self.session_id))}"
            )

        try:
            logger.debug(f"[尝试使用ChatGPT-API:{self.bot.engine}] 请求：{prompt}")
            self.bot.add_to_conversation(prompt, "user", session_id=self.session_id)
            start_time = time.time()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                'model': self.bot.engine,
                'messages': self.bot.conversation[self.session_id],
                'stream': True,
                'temperature': self.bot.temperature,
                'top_p': self.bot.top_p,
                'presence_penalty': self.bot.presence_penalty,
                'frequency_penalty': self.bot.frequency_penalty,
                "user": 'user',
                'max_tokens': self.bot.get_max_tokens(self.session_id, self.bot.engine),
            }
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(self.bot.timeout):
                    async with session.post(api_endpoint + '/v1/chat/completions', headers=headers,
                                            data=json.dumps(data), proxy=proxy) as resp:
                        if resp.status != 200:
                            response_text = await resp.text()
                            raise Exception(
                                f"{resp.status} {resp.reason} {response_text}",
                            )

                        response_role: str = ''
                        completion_text: str = ''

                        async for line in resp.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith("data: "):
                                line = line[len("data: "):]
                                if line == "[DONE]":
                                    break
                                if line:
                                    try:
                                        event = json.loads(line)
                                    except json.JSONDecodeError:
                                        raise Exception(f"Error when decoding line: {line}")
                                    event_time = time.time() - start_time
                                    if 'error' in event:
                                        raise Exception(f"{event['error']}")
                                    elif 'choices' in event and len(event['choices']) > 0 and 'delta' in \
                                            event['choices'][0]:
                                        if 'role' in event['choices'][0]['delta']:
                                            response_role = event['choices'][0]['delta']['role']
                                        if 'content' in event['choices'][0]['delta']:
                                            event_text = event['choices'][0]['delta']['content']
                                            completion_text += event_text
                                            yield completion_text

            self.bot.add_to_conversation(completion_text, response_role, session_id=self.session_id)
            token_count = self.bot.count_tokens(self.session_id, self.bot.engine)
            logger.debug(f"[ChatGPT-API:{self.bot.engine}] 响应：{completion_text}")
            logger.debug(f"[ChatGPT-API:{self.bot.engine}] 使用 token 数：{token_count}")
            logger.debug(f"[ChatGPT-API:{self.bot.engine}] 接收到全部消息花费了{event_time:.2f}秒")

        except Exception as e:
            logger.error(f"[ChatGPT-API:{self.bot.engine}] 请求失败：\n{e}")
            yield f"发生错误: \n{e}"

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
