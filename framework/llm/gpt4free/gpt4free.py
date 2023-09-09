from typing import Generator

import g4f

from config import G4fModels
from framework.accounts import account_manager
from framework.llm import Llm


class Gpt4FreeAdapter(Llm):
    """实例"""

    def __init__(self, session_id: str = "unknown", model: G4fModels = None):
        super().__init__(session_id)
        self.session_id = session_id
        self.model = model or account_manager.pick("gpt4free")
        self.conversation_history = []

    async def rollback(self):
        if len(self.conversation_history) <= 0:
            return False
        self.conversation_history = self.conversation_history[:-1]
        return True

    async def on_reset(self):
        self.conversation_history = []

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.conversation_history.append({'role': 'user', 'content': prompt})
        # FIXME: 删除 eval
        response = g4f.ChatCompletion.create(
            model=eval(
                self.model.model) if self.model.model.startswith("g4f.models.") else self.model.model,
            provider=eval(
                self.model.provider),
            messages=self.conversation_history,
        )
        self.conversation_history.append({'role': 'assistant', 'content': response})
        yield response
