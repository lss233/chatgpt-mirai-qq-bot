from typing import Generator

from framework.accounts import account_manager
from framework.exceptions import LlmRequestTimeoutException, LlmRequestFailedException
from framework.llm.llm import Llm
import httpx

from framework.llm.thudm.models import ChatGLMAPIInfo


class ChatGLM6BAdapter(Llm):
    """实例"""

    def __init__(self, session_id: str = "unknown"):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = account_manager.pick('chatglm-api')
        self.conversation_history = []
        self.client = httpx.AsyncClient()

    async def rollback(self):
        if len(self.conversation_history) <= 0:
            return False
        self.conversation_history = self.conversation_history[:-1]
        return True

    async def on_destoryed(self):
        self.conversation_history = []
        await self.client.aclose()
        self.account = account_manager.pick('chatglm-api')
        self.client = httpx.AsyncClient()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:
            response = await self.client.post(
                self.account.api_endpoint,
                timeout=self.account.timeout,
                headers={"Content-Type": "application/json"},
                json={"prompt": prompt, "history": self.conversation_history}
            )
            response.raise_for_status()
            ret = response.json()
            self.conversation_history = ret['history'][- self.account.max_turns:]
            yield ret['response']
        except httpx.TimeoutException as e:
            raise LlmRequestTimeoutException("chatglm-api") from e
        except httpx.HTTPStatusError as e:
            raise LlmRequestFailedException("chatglm-api") from e

    @classmethod
    def register(cls):
        account_manager.register_type("chatglm", ChatGLMAPIInfo)
