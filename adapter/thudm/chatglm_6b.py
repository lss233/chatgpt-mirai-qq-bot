from typing import Generator
from adapter.botservice import BotAdapter
import httpx
from constants import botManager


class ChatGLM6BAdapter(BotAdapter):
    """实例"""

    def __init__(self, session_id: str = "unknown"):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = botManager.pick('chatglm-api')
        self.conversation_history = []
        self.client = httpx.AsyncClient()

    async def rollback(self):
        if len(self.conversation_history) <= 0:
            return False
        self.conversation_history = self.conversation_history[:-1]
        return True

    async def on_reset(self):
        self.conversation_history = []
        await self.client.aclose()
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
        return
