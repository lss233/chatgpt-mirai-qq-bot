from abc import ABC, abstractmethod
from typing import Any, List
from framework.memory.entry import MemoryEntry


class MemoryComposer(ABC):
    """记忆组合器抽象类"""
    @abstractmethod
    def compose(self, message: Any) -> MemoryEntry:

        """将消息转换为记忆条目"""
        pass

class MemoryDecomposer(ABC):
    """记忆解析器抽象类"""
    @abstractmethod
    def decompose(self, entries: List[MemoryEntry]) -> str:
        """将记忆条目转换为字符串"""
        pass