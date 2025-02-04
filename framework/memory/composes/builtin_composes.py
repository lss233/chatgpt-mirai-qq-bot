from .base import MemoryComposer, MemoryDecomposer
from framework.memory.entry import MemoryEntry
from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from datetime import datetime
from typing import Any, List

class DefaultMemoryComposer(MemoryComposer):
    def compose(self, message: Any) -> MemoryEntry:
        if isinstance(message, IMMessage):
            # For IMMessage, use the type of the first message element
            message_type = message.message_elements[0].to_dict()["type"] if message.message_elements else "unknown"
            return MemoryEntry(
                sender=message.sender,
                content=message.content,
                timestamp=datetime.now(),
                metadata={"type": message_type}
            )
        else:  # LLMChatResponse
            # For LLM response, create a ChatSender for the assistant
            sender = ChatSender.from_c2c_chat(user_id="assistant")
            return MemoryEntry(
                sender=sender,
                content=message.choices[0].message.content,
                timestamp=datetime.now(),
                metadata={"type": "llm_response"}
            )

class DefaultMemoryDecomposer(MemoryDecomposer):
    def decompose(self, entries: List[MemoryEntry]) -> str:
        memory_texts = [
            f"[{m.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {m.sender}: {m.content}"
            for m in entries[-5:]  # 只返回最近5条
        ]
        return "\n".join(memory_texts)