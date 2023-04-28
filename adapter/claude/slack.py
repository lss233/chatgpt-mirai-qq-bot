import uuid

import json
from typing import Generator
from adapter.botservice import BotAdapter
from config import SlackAppAccessToken
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import httpx


class ClaudeInSlackAdapter(BotAdapter):
    account: SlackAppAccessToken
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = botManager.pick('slack-accesstoken')
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.client)
        self.conversation_id = None
        self.current_model = "claude"
        self.supported_models = [
            "claude"
        ]

    async def switch_model(self, model_name):
        self.current_model = model_name

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        await self.client.aclose()
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.client)
        self.conversation_id = None

    def __setup_headers(self, client):
        client.headers['Authorization'] = f"Bearer {self.account.channel_id}@{self.account.access_token}"
        client.headers['Content-Type'] = 'application/json;charset=UTF-8'
        client.headers[
            'User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        client.headers['Sec-Fetch-User'] = '?1'
        client.headers['Sec-Fetch-Mode'] = 'navigate'
        client.headers['Sec-Fetch-Site'] = 'none'
        client.headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        client.headers['Sec-Ch-Ua-Mobile'] = '?0'
        client.headers['Sec-Ch-Ua'] = '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'

    async def ask(self, prompt) -> Generator[str, None, None]:

        payload = {
            "action": "next",
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "author": {
                        "role": "user"
                    },
                    "content": {
                        "content_type": "text",
                        "parts": [
                            prompt
                        ]
                    }
                }
            ],
            "conversation_id": self.conversation_id,
            "parent_message_id": str(uuid.uuid4()),
            "model": self.current_model
        }

        async with self.client.stream(
                method="POST",
                url=f"{self.account.app_endpoint}conversation",
                json=payload,
                timeout=60
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or line is None:
                    continue
                if "data: " in line:
                    line = line[6:]
                if "[DONE]" in line:
                    break

                try:
                    line = json.loads(line)
                except json.decoder.JSONDecodeError:
                    continue

                message: str = line["message"]["content"]["parts"][0]
                self.conversation_id = line["conversation_id"]
                yield message

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role in {'assistant', 'claude'}:
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")
