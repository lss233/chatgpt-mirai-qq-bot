
from pydantic import BaseModel


class LLMChatMessage(BaseModel):
    content: str
    role: str