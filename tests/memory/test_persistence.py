import os
import shutil
import tempfile
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from framework.im.sender import ChatSender, ChatType
from framework.memory.entry import MemoryEntry
from framework.memory.persistences import FileMemoryPersistence, RedisMemoryPersistence

# ==================== 常量区 ====================
TEST_USER_1 = "user1"
TEST_USER_2 = "user2"
TEST_GROUP = "group1"
TEST_DISPLAY_NAME = "john"
TEST_CONTENT_1 = "test message 1"
TEST_CONTENT_2 = "test message 2"
TEST_METADATA_TEXT = {"type": "text"}
TEST_METADATA_IMAGE = {"type": "image"}
TEST_TIMESTAMP_1 = datetime(2024, 1, 1, 12, 0)
TEST_TIMESTAMP_2 = datetime(2024, 1, 1, 12, 1)
TEST_SCOPE = "test_scope"
INVALID_PATH = "\\\\?\\CON\\AUX\\NUL\\COM1\\LPT1;@#$"  # Windows 上的无效路径

# ==================== Fixtures ====================
@pytest.fixture
def test_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def file_persistence(test_dir):
    return FileMemoryPersistence(test_dir)

@pytest.fixture
def chat_senders():
    sender1 = ChatSender.from_group_chat(TEST_USER_1, TEST_GROUP, TEST_DISPLAY_NAME)
    sender2 = ChatSender.from_c2c_chat(TEST_USER_2, TEST_DISPLAY_NAME)
    return sender1, sender2

@pytest.fixture
def test_entries(chat_senders):
    sender1, sender2 = chat_senders
    return [
        MemoryEntry(
            sender=sender1,
            content=TEST_CONTENT_1,
            timestamp=TEST_TIMESTAMP_1,
            metadata=TEST_METADATA_TEXT
        ),
        MemoryEntry(
            sender=sender2,
            content=TEST_CONTENT_2,
            timestamp=TEST_TIMESTAMP_2,
            metadata=TEST_METADATA_IMAGE
        )
    ]

@pytest.fixture
def redis_mock():
    return MagicMock()

@pytest.fixture
def redis_persistence(redis_mock):
    with patch('redis.Redis', return_value=redis_mock):
        return RedisMemoryPersistence(host='localhost')

# ==================== 测试逻辑 ====================
class TestFileMemoryPersistence:
    def test_save_and_load(self, file_persistence, test_entries, test_dir):
        # 测试保存
        file_persistence.save(TEST_SCOPE, test_entries)
        
        # 验证文件是否创建
        file_path = os.path.join(test_dir, f"{TEST_SCOPE}.json")
        assert os.path.exists(file_path)
        
        # 测试加载
        loaded_entries = file_persistence.load(TEST_SCOPE)
        
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
        # 测试无效路径
        with pytest.raises(Exception):
            invalid_persistence = FileMemoryPersistence(INVALID_PATH)
            invalid_persistence.save(TEST_SCOPE, [])

class TestRedisMemoryPersistence:
    def test_save(self, redis_persistence, redis_mock, test_entries):
        # 测试保存
        redis_persistence.save(TEST_SCOPE, test_entries)
        redis_mock.set.assert_called_once()
        
    def test_load_with_data(self, redis_persistence, redis_mock, chat_senders):
        # Mock Redis 返回数据
        import json
        from framework.memory.persistences.codecs import MemoryJSONEncoder
        sender, _ = chat_senders
        serialized_data = [
            {
                "sender": {
                    "__type__": "ChatSender",
                    "user_id": sender.user_id,
                    "chat_type": sender.chat_type.value,
                    "group_id": sender.group_id,
                    "display_name": sender.display_name,
                    "raw_metadata": {}
                },
                "content": TEST_CONTENT_1,
                "timestamp": TEST_TIMESTAMP_1.isoformat(),
                "metadata": TEST_METADATA_TEXT
            }
        ]
        redis_mock.get.return_value = json.dumps(serialized_data, cls=MemoryJSONEncoder)
        
        # 测试加载
        loaded_entries = redis_persistence.load(TEST_SCOPE)
        
        # 验证数据
        assert len(loaded_entries) == 1
        entry = loaded_entries[0]
        assert entry.sender.user_id == TEST_USER_1
        assert entry.sender.chat_type == ChatType.GROUP
        assert entry.sender.group_id == TEST_GROUP
        assert entry.sender.display_name == TEST_DISPLAY_NAME
        assert entry.content == TEST_CONTENT_1
        assert entry.metadata == TEST_METADATA_TEXT

    def test_load_no_data(self, redis_persistence, redis_mock):
        redis_mock.get.return_value = None
        assert redis_persistence.load(TEST_SCOPE) == []