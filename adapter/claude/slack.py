import uuid

import json
from typing import Generator, Any

from accounts import account_manager, AccountInfoBaseModel
from adapter.botservice import BotAdapter
from exceptions import BotOperationNotSupportedException
from loguru import logger
import httpx


class SlackAccessTokenAuth(AccountInfoBaseModel):
    channel_id: str
    """负责与机器人交互的 Channel ID"""

    access_token: str
    """安装 Slack App 时获得的 access_token"""

    app_endpoint: str = "https://chatgpt-proxy.lss233.com/claude-in-slack/backend-api/"
    """API 的接入点"""

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client.headers['Authorization'] = f"Bearer {self.channel_id}@{self.access_token}"
        self._client.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self._client.headers[
            'User-Agent'
        ] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        self._client.headers['Sec-Fetch-User'] = '?1'
        self._client.headers['Sec-Fetch-Mode'] = 'navigate'
        self._client.headers['Sec-Fetch-Site'] = 'none'
        self._client.headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        self._client.headers['Sec-Ch-Ua-Mobile'] = '?0'
        self._client.headers['Sec-Ch-Ua'] = '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'

    def get_client(self) -> httpx.AsyncClient:
        return self._client

    async def check_alive(self) -> bool:
        """

        Successful response:
        ```
        ```
        {
            "items": []
        }
        ```
        ```
        Unsuccessful response: variety
        """
        req = await self._client.get(f"{self.app_endpoint}/conversations")
        return "items" in req.json()


class ClaudeInSlackAdapter(BotAdapter):
    account: SlackAccessTokenAuth
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = account_manager.pick('slack-accesstoken')
        self.client = self.account.get_client()
        self.conversation_id = None
        self.current_model = "claude"
        self.supported_models = [
            "claude"
        ]

    async def switch_model(self, model_name):
        self.current_model = model_name

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_destoryed(self):
        """重置会话"""
        ...

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
            async for item in self.ask(text):
                if item:
                    logger.debug(f"[预设] Chatbot 回应：{item}")

    @classmethod
    def register(cls):
        account_manager.register_type("slack", SlackAccessTokenAuth)
