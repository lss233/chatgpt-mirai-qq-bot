from typing import Generator
from adapter.botservice import BotAdapter
import httpx


class ChatGLM6BAdapter(BotAdapter):
    max_turns = 10
    """实例"""

    def __init__(self, session_id: str = "unknown"):
        super().__init__(session_id)
        self.session_id = session_id
        self.conversation_history = []
        self.client = httpx.AsyncClient()

    async def rollback(self):
        if len(self.conversation_history) > 0:
            self.conversation_history = self.conversation_history[:-1]
            return True
        else:
            return False

    async def on_reset(self):
        self.conversation_history = []
        await self.client.aclose()
        self.client = httpx.AsyncClient()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        response = await self.client.post(
            "http://127.0.0.1:7861",  # 本地chatglm的ip和端口
            timeout=120,
            headers={"Content-Type": "application/json"}, 
            json={"prompt": prompt, "history": self.conversation_history}
        )
        if response.status_code != 200:
            yield "出现了些错误!"
            return
        ret = response.json()
        self.conversation_history = ret['history'][- self.max_turns:]
        yield ret['response']
        return

    async def preset_ask(self, role: str, text: str):
        yield None
