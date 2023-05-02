import json
from typing import Generator

import httpx
import uuid
from loguru import logger

from framework.accounts import account_manager
from framework.exceptions import BotOperationNotSupportedException
from framework.llm.claude.models import SlackAccessTokenAuth
from framework.llm.llm import Llm


class ClaudeInSlackAdapter(Llm):
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
