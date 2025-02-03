import os
import shutil
import tempfile
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from framework.memory.memory_adapter import MemoryEntry
from framework.im.sender import ChatSender, ChatType
from framework.memory.persistence import FileMemoryPersistence, RedisMemoryPersistence

@pytest.fixture
def test_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def file_persistence(test_dir):
    return FileMemoryPersistence(test_dir)

@pytest.fixture
def test_entries():
    sender1 = ChatSender.from_group_chat("user1", "group1")
    sender2 = ChatSender.from_c2c_chat("user2")
    
    return [
        MemoryEntry(
            sender=sender1,
            content="test message 1",
            timestamp=datetime(2024, 1, 1, 12, 0),
            metadata={"type": "text"}
        ),
        MemoryEntry(
            sender=sender2,
            content="test message 2",
            timestamp=datetime(2024, 1, 1, 12, 1),
            metadata={"type": "image"}
        )
    ]

class TestFileMemoryPersistence:
    def test_save_and_load(self, file_persistence, test_entries, test_dir):
        # 测试保存
        file_persistence.save("test_scope", test_entries)
        
        # 验证文件是否创建
        file_path = os.path.join(test_dir, "test_scope.json")
        assert os.path.exists(file_path)
        
        # 测试加载
        loaded_entries = file_persistence.load("test_scope")
        
        # 验证加载的数据
        assert len(loaded_entries) == len(test_entries)
        for original, loaded in zip(test_entries, loaded_entries):
            assert original.sender.user_id == loaded.sender.user_id
            assert original.sender.chat_type == loaded.sender.chat_type
            assert original.sender.group_id == loaded.sender.group_id
            assert original.content == loaded.content
            assert original.timestamp == loaded.timestamp
            assert original.metadata == loaded.metadata
            
    def test_load_nonexistent(self, file_persistence):
        entries = file_persistence.load("nonexistent")
        assert entries == []
        
    def test_save_with_invalid_path(self):
        # 在Windows上，这些字符是不允许用在文件名中的
        with pytest.raises(Exception):
            invalid_persistence = FileMemoryPersistence("\\\\?\\CON\\AUX\\NUL\\COM1\\LPT1")
            invalid_persistence.save("test_scope", [])

class TestRedisMemoryPersistence:
    @pytest.fixture
    def redis_mock(self):
        return MagicMock()
        
    @pytest.fixture
    def redis_persistence(self, redis_mock):
        with patch('redis.Redis', return_value=redis_mock):
            return RedisMemoryPersistence(host='localhost')
            
    def test_save(self, redis_persistence, redis_mock, test_entries):
        # 测试保存
        redis_persistence.save("test_scope", test_entries)
        redis_mock.set.assert_called_once()
        
    def test_load_with_data(self, redis_persistence, redis_mock):
        # Mock Redis返回数据
        import json
        from framework.memory.persistence import MemoryJSONEncoder
        sender = ChatSender.from_group_chat("user1", "group1")
        serialized_data = [
            {
                "sender": {
                    "__type__": "ChatSender",
                    "user_id": sender.user_id,
                    "chat_type": sender.chat_type.value,
                    "group_id": sender.group_id,
                    "raw_metadata": {}
                },
                "content": "test message",
                "timestamp": "2024-01-01T12:00:00",
                "metadata": {"type": "text"}
            }
        ]
        redis_mock.get.return_value = json.dumps(serialized_data, cls=MemoryJSONEncoder)
        
        # 测试加载
        loaded_entries = redis_persistence.load("test_scope")
        
        # 验证数据
        assert len(loaded_entries) == 1
        entry = loaded_entries[0]
        assert entry.sender.user_id == "user1"
        assert entry.sender.chat_type == ChatType.GROUP
        assert entry.sender.group_id == "group1"
        assert entry.content == "test message"
        assert entry.metadata == {"type": "text"}
        
    def test_load_no_data(self, redis_persistence, redis_mock):
        redis_mock.get.return_value = None
        assert redis_persistence.load("test_scope") == [] 