from typing import Generator

import g4f

from adapter.botservice import BotAdapter
from adapter.common.chat_helper import ChatMessage, ROLE_ASSISTANT, ROLE_USER
from config import G4fModels
from constants import botManager


class Gpt4FreeAdapter(BotAdapter):
    """实例"""

    def __init__(self, session_id: str = "unknown", model: G4fModels = None):
        super().__init__(session_id)
        self.session_id = session_id
        self.model = model or botManager.pick("gpt4free")
        self.conversation_history = []

    async def rollback(self):
        if len(self.conversation_history) <= 0:
            return False
        self.conversation_history = self.conversation_history[:-1]
        return True

    async def on_reset(self):
        self.conversation_history = []

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.conversation_history.append(vars(ChatMessage(ROLE_USER, prompt)))
        response = g4f.ChatCompletion.create(
            model=eval(self.model.model) if self.model.model.startswith("g4f.models.") else self.model.model,
            provider=eval(self.model.provider),
            messages=self.conversation_history,
        )
        self.conversation_history.append(vars(ChatMessage(ROLE_ASSISTANT, response)))
        yield response
