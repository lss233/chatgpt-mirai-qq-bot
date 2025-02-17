from typing import Literal

from pydantic import BaseModel


class LLMChatMessage(BaseModel):
    content: str
    role: Literal["user", "assistant", "system"]
