import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, MemoryConfig
from framework.memory.memory_manager import MemoryManager
from framework.memory.memory_adapter import MemoryEntry, MemoryScope, MemoryComposer, MemoryDecomposer

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        # 创建模拟的容器和配置
        self.container = MagicMock(spec=DependencyContainer)
        self.config = GlobalConfig()
        self.container.resolve.return_value = self.config
        
        # 创建测试数据
        self.test_entry = MemoryEntry(
            sender="user1",
            content="test message",
            timestamp=datetime.now(),
            metadata={}
        )
        
        # 创建模拟的作用域
        self.mock_scope = MagicMock(spec=MemoryScope)
        self.mock_scope.get_scope_key.return_value = "test_scope"
        
        # 初始化管理器
        self.manager = MemoryManager(self.container)
        
    def test_init_file_persistence(self):
        # 测试文件持久化初始化
        config = GlobalConfig()
        config.memory.persistence.type = "file"
        self.container.resolve.return_value = config
        
        manager = MemoryManager(self.container)
        self.assertIsNotNone(manager.persistence)
        
    def test_init_redis_persistence(self):
        # 测试Redis持久化初始化
        config = GlobalConfig()
        config.memory.persistence.type = "redis"
        self.container.resolve.return_value = config
        
        with patch('framework.memory.persistence.RedisMemoryPersistence'):
            manager = MemoryManager(self.container)
            self.assertIsNotNone(manager.persistence)
            
    def test_init_invalid_persistence(self):
        # 测试无效的持久化类型
        config = GlobalConfig()
        config.memory.persistence.type = "invalid"
        self.container.resolve.return_value = config
        
        with self.assertRaises(ValueError):
            MemoryManager(self.container)
            
    def test_register_scope(self):
        # 测试注册作用域
        mock_scope_class = MagicMock(spec=MemoryScope)
        self.manager.register_scope("test", mock_scope_class)
        
        # 验证注册表
        self.assertIn("test", self.manager.scope_registry._registry)
        self.assertEqual(
            self.manager.scope_registry._registry["test"],
            mock_scope_class
        )
        
    def test_register_composer(self):
        # 测试注册组合器
        mock_composer_class = MagicMock(spec=MemoryComposer)
        self.manager.register_composer("test", mock_composer_class)
        
        # 验证注册表
        self.assertIn("test", self.manager.composer_registry._registry)
        self.assertEqual(
            self.manager.composer_registry._registry["test"],
            mock_composer_class
        )
        
    def test_register_decomposer(self):
        # 测试注册解析器
        mock_decomposer_class = MagicMock(spec=MemoryDecomposer)
        self.manager.register_decomposer("test", mock_decomposer_class)
        
        # 验证注册表
        self.assertIn("test", self.manager.decomposer_registry._registry)
        self.assertEqual(
            self.manager.decomposer_registry._registry["test"],
            mock_decomposer_class
        )
        
    def test_store_and_query(self):
        # Mock持久化层
        self.manager.persistence = MagicMock()
        self.manager.persistence.load.return_value = []
        
        # 测试存储
        self.manager.store(self.mock_scope, self.test_entry)
        
        # 验证内存缓存
        self.assertIn("test_scope", self.manager.memories)
        self.assertEqual(len(self.manager.memories["test_scope"]), 1)
        self.assertEqual(
            self.manager.memories["test_scope"][0],
            self.test_entry
        )
        
        # 验证持久化调用
        self.manager.persistence.save.assert_called_once_with(
            "test_scope",
            self.manager.memories["test_scope"]
        )
        
        # Mock作用域匹配
        self.mock_scope.is_in_scope.return_value = True
        
        # 测试查询
        results = self.manager.query(self.mock_scope, "user1")
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.test_entry)
        
    def test_max_entries_limit(self):
        # 设置最大条目数
        self.config.memory.max_entries = 2
        
        # Mock持久化层
        self.manager.persistence = MagicMock()
        self.manager.persistence.load.return_value = []
        
        # 存储3条记录
        for i in range(3):
            entry = MemoryEntry(
                sender=f"user{i}",
                content=f"message {i}",
                timestamp=datetime.now(),
                metadata={}
            )
            self.manager.store(self.mock_scope, entry)
            
        # 验证只保留了最新的2条
        self.assertEqual(
            len(self.manager.memories["test_scope"]),
            2
        )
        self.assertEqual(
            self.manager.memories["test_scope"][-1].content,
            "message 2"
        )
        
    def test_shutdown(self):
        # Mock持久化层
        self.manager.persistence = MagicMock()
        
        # 添加一些测试数据
        self.manager.memories = {
            "scope1": [self.test_entry],
            "scope2": [self.test_entry]
        }
        
        # 测试关闭
        self.manager.shutdown()
        
        # 验证所有数据都被保存
        self.assertEqual(
            self.manager.persistence.save.call_count,
            2
        )
        # 验证执行了flush
        self.manager.persistence.flush.assert_called_once() 