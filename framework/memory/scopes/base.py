from abc import ABC, abstractmethod

from framework.im.sender import ChatSender


class MemoryScope(ABC):
    """记忆作用域抽象类"""

    @abstractmethod
    def get_scope_key(self, sender: ChatSender) -> str:
        """获取作用域的键值"""

    @abstractmethod
    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        """判断是否在作用域内"""
