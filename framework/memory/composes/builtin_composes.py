from datetime import datetime, timedelta
from typing import List

from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.response import Message
from framework.memory.entry import MemoryEntry

from .base import ComposableMessageType, MemoryComposer, MemoryDecomposer


class DefaultMemoryComposer(MemoryComposer):
    def compose(
        self, sender: ChatSender, message: List[ComposableMessageType]
    ) -> MemoryEntry:
        composed_message = ""
        for msg in message:
            if isinstance(msg, IMMessage):
                composed_message += f"{sender.display_name} 说: {msg.content}\n"
            elif isinstance(msg, LLMChatMessage) or isinstance(msg, Message):
                composed_message += f"<@LLM> 说: {msg.content}\n"

        composed_message = composed_message.strip()
        composed_at = datetime.now()
        return MemoryEntry(
            sender=sender,
            content=composed_message,
            timestamp=composed_at,
        )


class DefaultMemoryDecomposer(MemoryDecomposer):
    def decompose(self, entries: List[MemoryEntry]) -> str:
        if len(entries) == 0:
            return self.empty_message

        # 7秒前，<记忆内容>
        memory_texts = []
        for entry in entries[-10:]:
            time_diff = datetime.now() - entry.timestamp
            time_str = self.get_time_str(time_diff)
            memory_texts.append(f"{time_str}，{entry.content}")

        return "\n".join(memory_texts)

    def get_time_str(self, time_diff: timedelta) -> str:
        if time_diff.days > 0:
            return f"{time_diff.days}天前"
        elif time_diff.seconds > 3600:
            return f"{time_diff.seconds // 3600}小时前"
        elif time_diff.seconds > 60:
            return f"{time_diff.seconds // 60}分钟前"
        else:
            return "刚刚"
