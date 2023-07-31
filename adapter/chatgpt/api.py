import json
import time
import aiohttp
import async_timeout
import tiktoken
from loguru import logger
from typing import AsyncGenerator

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager, config

DEFAULT_ENGINE: str = "gpt-3.5-turbo"


class OpenAIChatbot:
    def __init__(self, api_info: OpenAIAPIKey):
        self.api_key = api_info.api_key
        self.proxy = api_info.proxy
        self.presence_penalty = config.openai.gpt_params.presence_penalty
        self.frequency_penalty = config.openai.gpt_params.frequency_penalty
        self.top_p = config.openai.gpt_params.top_p
        self.temperature = config.openai.gpt_params.temperature
        self.max_tokens = config.openai.gpt_params.max_tokens
        self.engine = api_info.model or DEFAULT_ENGINE
        self.timeout = config.response.max_timeout
        self.conversation: dict[str, list[dict]] = {
            "default": [
                {
                    "role": "system",
                    "content": "You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2021-09\nCurrent date:[current date]",
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

    def add_to_conversation(self, message: str, role: str, session_id: str = "default") -> None:
        if role and message is not None:
            self.conversation[session_id].append({"role": role, "content": message})
        else:
            logger.warning("出现错误！返回消息为空，不添加到会话。")
            raise ValueError("出现错误！返回消息为空，不添加到会话。")

    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def count_tokens(self, session_id: str = "default", model: str = DEFAULT_ENGINE):
        """Return the number of tokens used by a list of messages."""
        if model is None:
            model = DEFAULT_ENGINE
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens_per_message = 4
        tokens_per_name = 1

        num_tokens = 0
        for message in self.conversation[session_id]:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if value is not None:
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

    def __init__(self, session_id: str = "unknown"):
        self.latest_role = None
        self.__conversation_keep_from = 0
        self.session_id = session_id
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(self.api_info)
        self.conversation_id = None
        self.parent_id = None
        super().__init__()
        self.bot.conversation[self.session_id] = []
        self.current_model = self.bot.engine
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

    def manage_conversation(self, session_id: str, prompt: str):
        if session_id not in self.bot.conversation:
            self.bot.conversation[session_id] = [
                {"role": "system", "content": prompt}
            ]
            self.__conversation_keep_from = 1

        while self.bot.max_tokens - self.bot.count_tokens(session_id) < config.openai.gpt_params.min_tokens and \
                len(self.bot.conversation[session_id]) > self.__conversation_keep_from:
            self.bot.conversation[session_id].pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(self.bot.count_tokens(session_id))}"
            )

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
        self.bot.engine = self.current_model
        self.__conversation_keep_from = 0

    def construct_data(self, messages: list = None, api_key: str = None, stream: bool = True):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        data = {
            'model': self.bot.engine,
            'messages': messages,
            'stream': stream,
            'temperature': self.bot.temperature,
            'top_p': self.bot.top_p,
            'presence_penalty': self.bot.presence_penalty,
            'frequency_penalty': self.bot.frequency_penalty,
            "user": 'user',
            'max_tokens': self.bot.get_max_tokens(self.session_id, self.bot.engine),
        }
        return headers, data

    def _prepare_request(self, session_id: str = None, messages: list = None, stream: bool = False):
        self.api_info = botManager.pick('openai-api')
        api_key = self.api_info.api_key
        proxy = self.api_info.proxy
        api_endpoint = config.openai.api_endpoint or "https://api.openai.com/v1"

        if not messages:
            messages = self.bot.conversation[session_id]

        headers, data = self.construct_data(messages, api_key, stream)

        return proxy, api_endpoint, headers, data

    async def _process_response(self, resp, session_id: str = None):

        result = await resp.json()

        total_tokens = result.get('usage', {}).get('total_tokens', None)
        logger.debug(f"[ChatGPT-API:{self.bot.engine}] 使用 token 数：{total_tokens}")
        if total_tokens is None:
            raise Exception("Response does not contain 'total_tokens'")

        content = result.get('choices', [{}])[0].get('message', {}).get('content', None)
        logger.debug(f"[ChatGPT-API:{self.bot.engine}] 响应：{content}")
        if content is None:
            raise Exception("Response does not contain 'content'")

        response_role = result.get('choices', [{}])[0].get('message', {}).get('role', None)
        if response_role is None:
            raise Exception("Response does not contain 'role'")

        self.bot.add_to_conversation(content, response_role, session_id)

        return content

    async def request(self, session_id: str = None, messages: list = None) -> str:
        proxy, api_endpoint, headers, data = self._prepare_request(session_id, messages, stream=False)

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(self.bot.timeout):
                async with session.post(f'{api_endpoint}/chat/completions', headers=headers,
                                                    data=json.dumps(data), proxy=proxy) as resp:
                    if resp.status != 200:
                        response_text = await resp.text()
                        raise Exception(
                            f"{resp.status} {resp.reason} {response_text}",
                        )
                    return await self._process_response(resp, session_id)

    async def request_with_stream(self, session_id: str = None, messages: list = None) -> AsyncGenerator[str, None]:
        proxy, api_endpoint, headers, data = self._prepare_request(session_id, messages, stream=True)

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(self.bot.timeout):
                async with session.post(f'{api_endpoint}/chat/completions', headers=headers, data=json.dumps(data),
                                        proxy=proxy) as resp:
                    if resp.status != 200:
                        response_text = await resp.text()
                        raise Exception(
                            f"{resp.status} {resp.reason} {response_text}",
                        )

                    response_role: str = ''
                    completion_text: str = ''

                    async for line in resp.content:
                        try:
                            line = line.decode('utf-8').strip()
                            if not line.startswith("data: "):
                                continue
                            line = line[len("data: "):]
                            if line == "[DONE]":
                                break
                            if not line:
                                continue
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            raise Exception(f"JSON解码错误: {line}") from None
                        except Exception as e:
                            logger.error(f"未知错误: {e}\n响应内容: {resp.content}")
                            logger.error("请将该段日记提交到项目issue中，以便修复该问题。")
                            raise Exception(f"未知错误: {e}") from None
                        if 'error' in event:
                            raise Exception(f"响应错误: {event['error']}")
                        if 'choices' in event and len(event['choices']) > 0 and 'delta' in event['choices'][0]:
                            delta = event['choices'][0]['delta']
                            if 'role' in delta:
                                if delta['role'] is not None:
                                    response_role = delta['role']
                            if 'content' in delta:
                                event_text = delta['content']
                                if event_text is not None:
                                    completion_text += event_text
                                    self.latest_role = response_role
                                    yield event_text
        self.bot.add_to_conversation(completion_text, response_role, session_id)

    async def compressed_session(self, session_id: str):
        if session_id not in self.bot.conversation or not self.bot.conversation[session_id]:
            logger.debug(f"不存在该会话，不进行压缩: {session_id}")
            return

        if self.bot.count_tokens(session_id) > config.openai.gpt_params.compressed_tokens:
            logger.debug('开始进行会话压缩')

            filtered_data = [entry for entry in self.bot.conversation[session_id] if entry['role'] != 'system']
            self.bot.conversation[session_id] = [entry for entry in self.bot.conversation[session_id] if
                                                 entry['role'] not in ['assistant', 'user']]

            filtered_data.append(({"role": "system",
                                   "content": "Summarize the discussion briefly in 200 words or less to use as a prompt for future context."}))

            async for text in self.request_with_stream(session_id=session_id, messages=filtered_data):
                pass

            token_count = self.bot.count_tokens(self.session_id, self.bot.engine)
            logger.debug(f"压缩会话后使用 token 数：{token_count}")

    async def ask(self, prompt: str) -> AsyncGenerator[str, None]:
        """Send a message to api and return the response with stream."""

        self.manage_conversation(self.session_id, prompt)

        if config.openai.gpt_params.compressed_session:
            await self.compressed_session(self.session_id)

        event_time = None

        try:
            if self.bot.engine not in self.supported_models:
                logger.warning(f"当前模型非官方支持的模型，请注意控制台输出，当前使用的模型为 {self.bot.engine}")
            logger.debug(f"[尝试使用ChatGPT-API:{self.bot.engine}] 请求：{prompt}")
            self.bot.add_to_conversation(prompt, "user", session_id=self.session_id)
            start_time = time.time()

            full_response = ''

            if config.openai.gpt_params.stream:
                async for resp in self.request_with_stream(session_id=self.session_id):
                    full_response += resp
                    yield full_response

                token_count = self.bot.count_tokens(self.session_id, self.bot.engine)
                logger.debug(f"[ChatGPT-API:{self.bot.engine}] 响应：{full_response}")
                logger.debug(f"[ChatGPT-API:{self.bot.engine}] 使用 token 数：{token_count}")
            else:
                yield await self.request(session_id=self.session_id)
            event_time = time.time() - start_time
            if event_time is not None:
                logger.debug(f"[ChatGPT-API:{self.bot.engine}] 接收到全部消息花费了{event_time:.2f}秒")

        except Exception as e:
            logger.error(f"[ChatGPT-API:{self.bot.engine}] 请求失败：\n{e}")
            yield f"发生错误: \n{e}"
            raise

    async def preset_ask(self, role: str, text: str):
        self.bot.engine = self.current_model
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
