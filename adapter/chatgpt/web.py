from typing import Generator

from adapter.botservice import BotAdapter

from revChatGPT.V1 import Chatbot as OpenAIChatbot


class ChatGPTWebAdapter(BotAdapter):
    conversation_id: str
    """会话 ID"""

    parent_id: str
    """上文 ID"""

    conversation_id_prev_queue = []
    parent_id_prev_queue = []

    bot: OpenAIChatbot
    """实例"""

    def __int__(self):
        self.conversation_id = None
        self.parent_id = None

    async def rollback(self):
        self.conversation_id = self.conversation_id_prev_queue.pop()
        self.parent_id = self.parent_id_prev_queue.pop()

    async def on_reset(self):
        if self.conversation_id is not None:
            self.bot.delete_conversation(self.conversation_id)

    async def ask(self, prompt: str) -> Generator[str]:
        yield self.bot.ask(prompt, self.conversation_id, self.parent_id)