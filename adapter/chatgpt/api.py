from typing import Generator, Union

import asyncio
import janus
import openai
from loguru import logger

from adapter.botservice import BotAdapter
from revChatGPT.V3 import Chatbot

from config import OpenAIAPIKey
from constants import botManager, config
import ctypes
import json

hashu = lambda word: ctypes.c_uint64(hash(word)).value


class OpenAIChatbot(Chatbot):
    def ask_stream(self, prompt: str, role: str = "user", **kwargs) -> str:
        """
        Ask a question
        """
        api_key = kwargs.get("api_key")
        self.__add_to_conversation(prompt, "user")
        self.__truncate_conversation()
        # Get response
        if self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
        response = self.session.post(
            f"{openai.api_base}/chat/completions",
            headers={"Authorization": "Bearer " + (api_key or self.api_key)},
            json={
                "model": self.engine,
                "messages": self.conversation,
                "stream": True,
                # kwargs
                "temperature": config.openai.api_params.temperature,
                "top_p": config.openai.api_params.top_p,
                "presence_penalty": config.openai.api_params.presence_penalty,
                "frequency_penalty": config.openai.api_params.frequency_penalty,
                "n": 1,
                "user": role,
                "max_tokens": config.openai.api_params.max_tokens,
            },
            stream=True,
        )
        if response.status_code != 200:
            raise Exception(
                f"Error: {response.status_code} {response.reason} {response.text}",
            )
        response_role: str = None
        full_response: str = ""
        for line in response.iter_lines():
            print(line)
            if not line:
                continue
            # Remove "data: "
            line = line.decode("utf-8")[6:]
            if line == "[DONE]":
                break
            resp: dict = json.loads(line)
            choices = resp.get("choices")
            if not choices:
                continue
            delta = choices[0].get("delta")
            if not delta:
                continue
            if "role" in delta:
                response_role = delta["role"]
            if "content" in delta:
                content = delta["content"]
                full_response += content
                yield content
        self.__add_to_conversation(full_response, response_role)


class ChatGPTAPIAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None
    """API Key"""

    bot: OpenAIChatbot = None
    """实例"""

    hashed_user_id: str

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.hashed_user_id = "user-" + hashu("session_id").to_bytes(8, "big").hex()
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(api_key=self.api_info.api_key, proxy=self.api_info.proxy)
        self.conversation_id = None
        self.parent_id = None
        super().__init__()

    async def rollback(self):
        if len(self.bot.conversation) > 0:
            self.bot.rollback()
            return True
        else:
            return False

    async def on_reset(self):
        self.bot.conversation = []
        self.api_info = botManager.pick('openai-api')
        self.bot = OpenAIChatbot(api_key=self.api_info.api_key, proxy=self.api_info.proxy)

    def ask_sync(self, sync_q, prompt):
        try:
            for resp in self.bot.ask_stream(prompt, role=self.hashed_user_id):
                sync_q.put(resp)
            sync_q.put(None)
        except Exception as e:
            sync_q.put(e)
        sync_q.join()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        full_response = ''
        queue: janus.Queue[Union[str, Exception, None]] = janus.Queue()
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, self.ask_sync, queue.sync_q, prompt)
        while not queue.async_q.closed:
            resp = await queue.async_q.get()
            queue.async_q.task_done()
            if isinstance(resp, Exception):
                # 出现了错误
                raise resp
            elif resp is None:
                # 发完了
                break
            full_response += resp
            yield full_response
        await future
        queue.close()
        await queue.wait_closed()
        logger.debug("[ChatGPT-API] 响应：" + full_response)

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role == 'chatgpt':
            logger.debug(f"[预设] 响应：{text}")
            yield text
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        self.bot.conversation.append({"role": role, "content": text})
