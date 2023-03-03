from typing import List

from adapter.botservice import BotAdapter
from renderer.renderer import Renderer

handlers = dict()

class ConversationContext:
    adapter: BotAdapter
    renderer: Renderer

    async def reset(self):
        pass

    async def ask(self, prompt: str, name: str = None):
        async with self.renderer.session() as session:
            for item in self.adapter.ask(prompt):
                session.render(item)
            return session.result()

    def rollback(self):
        pass

class ConversationHandler:
    """
    每个聊天窗口拥有一个 ConversationHandler，
    负责管理多个不同的 ConversationContext
    """
    conversations = []
    """当前聊天窗口下所有的会话"""

    current_conversation: ConversationContext = None

    def __int__(self, ):
        ...

    def list(self) -> List[ConversationContext]:
        ...

    """创建新的上下文"""

    def create(self, _type: str):
        if len(self.conversations) < 0:
            conversation = ConversationContext(_type)
            self.conversations.append(conversation)

    """切换对话上下文"""

    def switch(self, index: int) -> bool:
        if len(self.conversations) > index:
            self.current_conversation = self.conversations[index]
            return True
        return False

    @classmethod
    def get_handler(cls, session_id: str):
        if session_id not in handlers:
            handlers[session_id] = ConversationHandler()
        return handlers[session_id]
