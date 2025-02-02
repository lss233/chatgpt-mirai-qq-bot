from typing import Dict, List, Optional
from datetime import datetime

from framework.ioc.container import DependencyContainer

class MemoryEntry:
    def __init__(self, sender: str, content: str, timestamp: datetime):
        self.sender = sender
        self.content = content
        self.timestamp = timestamp

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
            MemoryEntry(sender, content, datetime.now())
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