from typing import List

from adapter.botservice import BotAdapter


class ConversationContext:
    adapter: BotAdapter
    async def reset(self):
        pass
    async def ask(self, prompt: str, name: str = None):
        yield self.adapter.ask(prompt)
class ConversationManager:
    def list(self, id: str) -> List[ConversationContext]: ...

    def create(self, id: str): ...

