ROLE_USER: str = "user"
ROLE_ASSISTANT: str = "assistant"


class ChatMessage:

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
