import json
import os
from typing import Dict, List
from datetime import datetime
from .memory_adapter import MemoryEntry, MemoryPersistence
from abc import ABC, abstractmethod
import redis
from ..im.sender import ChatSender, ChatType

class MemoryJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ChatSender):
            return {
                "__type__": "ChatSender",
                "user_id": obj.user_id,
                "chat_type": obj.chat_type.value,
                "group_id": obj.group_id,
                "raw_metadata": obj.raw_metadata
            }
        elif isinstance(obj, ChatType):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def memory_json_decoder(obj):
    if "__type__" in obj:
        if obj["__type__"] == "ChatSender":
            return ChatSender(
                user_id=obj["user_id"],
                chat_type=ChatType(obj["chat_type"]),
                group_id=obj["group_id"],
                raw_metadata=obj["raw_metadata"]
            )
    return obj

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

class RedisMemoryPersistence(MemoryPersistence):
    """Redis持久化实现"""
    def __init__(self, redis_url: str = None, host: str = 'localhost', port: int = 6379, db: int = 0):
        if redis_url:
            self.redis = redis.from_url(redis_url)
        else:
            self.redis = redis.Redis(host=host, port=port, db=db)
        
    def save(self, scope_key: str, entries: List[MemoryEntry]) -> None:
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
        
        # 存储到Redis
        self.redis.set(
            scope_key,
            json.dumps(serialized_entries, ensure_ascii=False, cls=MemoryJSONEncoder)
        )
        
    def load(self, scope_key: str) -> List[MemoryEntry]:
        # 从Redis读取
        data = self.redis.get(scope_key)
        if not data:
            return []
            
        # 反序列化
        serialized_entries = json.loads(data, object_hook=memory_json_decoder)
        
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
        self.redis.save() 