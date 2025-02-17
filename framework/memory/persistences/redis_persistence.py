import json
from datetime import datetime
from typing import List

from framework.memory.entry import MemoryEntry

from .base import MemoryPersistence
from .codecs import MemoryJSONEncoder, memory_json_decoder


class RedisMemoryPersistence(MemoryPersistence):
    """Redis持久化实现"""

    def __init__(
        self,
        redis_url: str = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
    ):
        import redis

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
                "metadata": entry.metadata,
            }
            for entry in entries
        ]

        # 存储到Redis
        self.redis.set(
            scope_key,
            json.dumps(serialized_entries, ensure_ascii=False, cls=MemoryJSONEncoder),
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
                timestamp=(
                    datetime.fromisoformat(entry["timestamp"])
                    if isinstance(entry["timestamp"], str)
                    else entry["timestamp"]
                ),
                metadata=entry["metadata"],
            )
            for entry in serialized_entries
        ]

    def flush(self) -> None:
        self.redis.save()
