from typing import Callable, Optional

from framework.conversation import ConversationContext


class Middleware:
    async def handle_request(self, session_id: str, prompt: str, respond: Callable,
                             conversation_context: Optional[ConversationContext], action: Callable):
        await action(session_id, prompt, conversation_context, respond)

    async def handle_respond(self, session_id: str, prompt: str, rendered: str, respond: Callable, action: Callable):
        await action(session_id, prompt, rendered, respond)

    async def on_respond(self, session_id: str, prompt: str, rendered: str): ...
    async def handle_respond_completed(self, session_id: str, prompt: str, respond: Callable): ...
