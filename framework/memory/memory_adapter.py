from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import threading
from queue import Queue
import json

from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from ..im.sender import ChatSender
from ..im.sender import ChatType

@dataclass
class MemoryEntry:
    """基础记忆条目"""
    sender: ChatSender
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]

class MemoryScope(ABC):
    """记忆作用域抽象类"""
    @abstractmethod
    def get_scope_key(self, sender: ChatSender) -> str:
        """获取作用域的键值"""
        pass
    
    @abstractmethod
    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        """判断是否在作用域内"""
        pass

class MemoryPersistence(ABC):
    """持久化层抽象类"""
    @abstractmethod
    def save(self, scope_key: str, entries: List[MemoryEntry]) -> None:
        pass
        
    @abstractmethod
    def load(self, scope_key: str) -> List[MemoryEntry]:
        pass
        
    @abstractmethod
    def flush(self) -> None:
        """确保所有数据都已持久化"""
        pass

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

# 默认实现
class MemberScope(MemoryScope):
    """群成员作用域"""
    def get_scope_key(self, sender: ChatSender) -> str:
        if sender.chat_type == ChatType.GROUP:
            return f"member:{sender.group_id}:{sender.user_id}"
        else:
            return f"c2c:{sender.user_id}"
    
    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        if target_sender.chat_type != query_sender.chat_type:
            return False
            
        if target_sender.chat_type == ChatType.GROUP:
            return (target_sender.group_id == query_sender.group_id and 
                   target_sender.user_id == query_sender.user_id)
        else:
            return target_sender.user_id == query_sender.user_id

class GroupScope(MemoryScope):
    """群作用域"""
    def get_scope_key(self, sender: ChatSender) -> str:
        if sender.chat_type == ChatType.GROUP:
            return f"group:{sender.group_id}"
        else:
            return f"c2c:{sender.user_id}"
    
    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        if target_sender.chat_type != query_sender.chat_type:
            return False
            
        if target_sender.chat_type == ChatType.GROUP:
            return target_sender.group_id == query_sender.group_id
        else:
            return target_sender.user_id == query_sender.user_id

class GlobalScope(MemoryScope):
    """全局作用域"""
    def get_scope_key(self, sender: ChatSender) -> str:
        return "global"
    
    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        return True

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

class AsyncMemoryPersistence:
    """异步持久化管理器"""
    def __init__(self, persistence: MemoryPersistence):
        self.persistence = persistence
        self.queue = Queue()
        self.running = True
        self.worker = threading.Thread(target=self._worker)
        self.worker.start()
        
    def _worker(self):
        while self.running:
            try:
                scope_key, entries = self.queue.get(timeout=1)
                self.persistence.save(scope_key, entries)
                self.queue.task_done()
                print(f"Saved {scope_key} with {len(entries)} entries")
            except:
                continue
                
    def save(self, scope_key: str, entries: List[MemoryEntry]):
        self.queue.put((scope_key, entries))
        
    def stop(self):
        self.running = False
        self.worker.join()
        self.persistence.flush()

class MemoryManager:
    def __init__(self, 
                 persistence: MemoryPersistence,
                 max_entries: int = 10):
        self.persistence = AsyncMemoryPersistence(persistence)
        self.max_entries = max_entries
        self.memories: Dict[str, List[MemoryEntry]] = {}
        
    def store(self, scope: MemoryScope, entry: MemoryEntry) -> None:
        """存储新的记忆"""
        scope_key = scope.get_scope_key(entry.sender)
        
        if scope_key not in self.memories:
            self.memories[scope_key] = self.persistence.persistence.load(scope_key)
            
        self.memories[scope_key].append(entry)
        
        if len(self.memories[scope_key]) > self.max_entries:
            self.memories[scope_key] = self.memories[scope_key][-self.max_entries:]
            
        self.persistence.save(scope_key, self.memories[scope_key])

    def query(self, scope: MemoryScope, sender: ChatSender) -> List[MemoryEntry]:
        """查询历史记忆"""
        relevant_memories = []
        
        # 遍历所有记忆，找出作用域内的记忆
        for scope_key, entries in self.memories.items():
            for entry in entries:
                if scope.is_in_scope(entry.sender, sender):
                    relevant_memories.append(entry)
                    
        # 按时间排序
        relevant_memories.sort(key=lambda x: x.timestamp)
        return relevant_memories

    def shutdown(self):
        """程序退出时调用，确保所有数据都已持久化"""
        self.persistence.stop()

class MemoryAdapter:
    def __init__(self, container: DependencyContainer, max_entries: int = 10):
        self.container = container
        self.memories: Dict[str, List[MemoryEntry]] = {}
        self.max_entries = max_entries

    def store(self, sender: str, content: str) -> None:
        """存储新的记忆"""
        if sender not in self.memories:
            self.memories[sender] = []
            
        # 添加新记忆
        self.memories[sender].append(
            MemoryEntry(sender, content, datetime.now(), {})
        )
        
        # 保持最大记忆数量
        if len(self.memories[sender]) > self.max_entries:
            self.memories[sender] = self.memories[sender][-self.max_entries:]

    def query(self, sender: str, content: Optional[str] = None) -> str:
        """查询历史记忆
        可以根据发送者和当前内容进行相关性查询
        这里实现一个简单版本，直接返回最近的几条记忆
        """
        if sender not in self.memories:
            return ""
            
        # 简单地将最近的记忆组合成字符串
        memory_texts = [
            f"[{m.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {m.sender}: {m.content}"
            for m in self.memories[sender][-5:]  # 只返回最近5条
        ]
        
        return "\n".join(memory_texts) 