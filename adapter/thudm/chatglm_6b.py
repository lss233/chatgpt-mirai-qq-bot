from typing import Generator

from accounts import account_manager, AccountInfoBaseModel
from adapter.botservice import BotAdapter
import httpx


class ChatGLMAPIInfo(AccountInfoBaseModel):
    api_endpoint: str
    """自定义 ChatGLM API 的接入点"""
    max_turns: int = 10
    """最大对话轮数"""
    timeout: int = 120
    """请求超时时间（单位：秒）"""

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.api_endpoint,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                json={}
            )
            return True


class ChatGLM6BAdapter(BotAdapter):
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

    @classmethod
    def register(cls):
        account_manager.register_type("chatglm", ChatGLMAPIInfo)
