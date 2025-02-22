from abc import ABC, abstractmethod
from typing import List, Union

from kirara_ai.im.message import IMMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.llm.format.message import LLMChatMessage
from kirara_ai.llm.format.response import Message
from kirara_ai.memory.entry import MemoryEntry

# 可组合的消息类型
ComposableMessageType = Union[IMMessage, LLMChatMessage, Message, str]


class MemoryComposer(ABC):
    """记忆组合器抽象类"""

    @abstractmethod
    def compose(
        self, sender: ChatSender, message: List[ComposableMessageType]
    ) -> MemoryEntry:
        """将消息转换为记忆条目"""


class MemoryDecomposer(ABC):
    """记忆解析器抽象类"""

    @abstractmethod
    def decompose(self, entries: List[MemoryEntry]) -> str:
        """将记忆条目转换为字符串"""

    @property
    def empty_message(self) -> str:
        """空记忆消息"""
        return "<空记忆>"
