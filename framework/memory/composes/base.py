from abc import ABC, abstractmethod
from typing import Any, List, Union
from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.response import Message
from framework.memory.entry import MemoryEntry

# 可组合的消息类型
ComposableMessageType = Union[IMMessage, LLMChatMessage, Message, str]

class MemoryComposer(ABC):
    """记忆组合器抽象类"""
    @abstractmethod
    def compose(self, sender: ChatSender, message: List[ComposableMessageType]) -> MemoryEntry:
        """将消息转换为记忆条目"""
        pass


class MemoryDecomposer(ABC):
    """记忆解析器抽象类"""
    @abstractmethod
    def decompose(self, entries: List[MemoryEntry]) -> str:
        """将记忆条目转换为字符串"""
        pass

    @property
    def empty_message(self) -> str:
        """空记忆消息"""
        return "<空记忆>"

