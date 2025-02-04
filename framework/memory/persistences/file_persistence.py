import os
import json
from datetime import datetime
from typing import List
from framework.memory.entry import MemoryEntry
from .codecs import MemoryJSONEncoder, memory_json_decoder
from .base import MemoryPersistence

class FileMemoryPersistence(MemoryPersistence):
    """文件持久化实现"""
    def __init__(self, data_dir: str):
        if not os.path.isabs(data_dir):
            data_dir = os.path.abspath(data_dir)
            
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def _get_file_path(self, scope_key: str) -> str:
        scope_key = scope_key.replace(":", "_")
        return os.path.join(self.data_dir, f"{scope_key}.json")
        
    def save(self, scope_key: str, entries: List[MemoryEntry]) -> None:
        file_path = self._get_file_path(scope_key)
        
        # 序列化记忆条目
        serialized_entries = [
            {
                "sender": entry.sender,
                "content": entry.content,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata
            }
            for entry in entries
        ]
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serialized_entries, f, ensure_ascii=False, indent=2, cls=MemoryJSONEncoder)
            
    def load(self, scope_key: str) -> List[MemoryEntry]:
        file_path = self._get_file_path(scope_key)
        
        if not os.path.exists(file_path):
            return []
            
        # 读取并反序列化
        with open(file_path, "r", encoding="utf-8") as f:
            serialized_entries = json.load(f, object_hook=memory_json_decoder)
            
        return [
            MemoryEntry(
                sender=entry["sender"],
                content=entry["content"],
                timestamp=datetime.fromisoformat(entry["timestamp"]) if isinstance(entry["timestamp"], str) else entry["timestamp"],
                metadata=entry["metadata"]
            )
            for entry in serialized_entries
        ]
        
    def flush(self) -> None:
        # 文件系统实现不需要特别的flush操作
        pass