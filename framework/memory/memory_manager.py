from typing import Dict, List, Optional, Type
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig
from framework.memory.persistences.base import AsyncMemoryPersistence
from framework.memory.persistences.file_persistence import FileMemoryPersistence
from framework.memory.persistences.redis_persistence import RedisMemoryPersistence
from .entry import MemoryEntry
from .scopes import MemoryScope
from .composes import MemoryComposer, MemoryDecomposer
from .registry import ScopeRegistry, ComposerRegistry, DecomposerRegistry


class MemoryManager:
    """记忆系统管理器，负责整个记忆系统的生命周期管理"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.config = container.resolve(GlobalConfig).memory
        
        # 初始化注册表
        self.scope_registry = ScopeRegistry()
        self.composer_registry = ComposerRegistry()
        self.decomposer_registry = DecomposerRegistry()
        
        # 注册到容器
        container.register(ScopeRegistry, self.scope_registry)
        container.register(ComposerRegistry, self.composer_registry)
        container.register(DecomposerRegistry, self.decomposer_registry)
        
        # 初始化持久化层
        self._init_persistence()
        
        # 内存缓存
        self.memories: Dict[str, List[MemoryEntry]] = {}
        
    def _init_persistence(self):
        """初始化持久化层"""
        persistence_type = self.config.persistence.type
        
        if persistence_type == "file":
            storage_dir = self.config.persistence.file["storage_dir"]
            self.persistence = FileMemoryPersistence(storage_dir)
        elif persistence_type == "redis":
            redis_config = self.config.persistence.redis
            self.persistence = RedisMemoryPersistence(**redis_config)
        else:
            raise ValueError(f"Unsupported persistence type: {persistence_type}")
        
        self.persistence = AsyncMemoryPersistence(self.persistence)

    def register_scope(self, name: str, scope_class: Type[MemoryScope]):
        """注册新的作用域类型"""
        self.scope_registry.register(name, scope_class)
        
    def register_composer(self, name: str, composer_class: Type[MemoryComposer]):
        """注册新的组合器"""
        self.composer_registry.register(name, composer_class)
        
    def register_decomposer(self, name: str, decomposer_class: Type[MemoryDecomposer]):
        """注册新的解析器"""
        self.decomposer_registry.register(name, decomposer_class)
        
    def store(self, scope: MemoryScope, entry: MemoryEntry) -> None:
        """存储新的记忆"""
        scope_key = scope.get_scope_key(entry.sender)
        
        if scope_key not in self.memories:
            self.memories[scope_key] = self.persistence.load(scope_key)
            
        self.memories[scope_key].append(entry)
        
        if len(self.memories[scope_key]) > self.config.max_entries:
            self.memories[scope_key] = self.memories[scope_key][-self.config.max_entries:]
            
        self.persistence.save(scope_key, self.memories[scope_key])
        
    def query(self, scope: MemoryScope, sender: str) -> List[MemoryEntry]:
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
        """关闭记忆系统，确保数据持久化"""
        # 保存所有内存中的数据
        for scope_key, entries in self.memories.items():
            self.persistence.save(scope_key, entries)
        # 执行持久化层的flush操作
        self.persistence.stop()