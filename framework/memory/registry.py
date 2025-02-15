from typing import Dict, Type
from framework.memory.scopes import MemoryScope
from framework.memory.composes import MemoryComposer, MemoryDecomposer

class Registry:
    """基础注册表类"""
    def __init__(self):
        self._registry: Dict[str, Type] = {}
        
    def register(self, name: str, cls: Type) -> None:
        """注册一个新的实现"""
        self._registry[name] = cls
        
    def unregister(self, name: str) -> None:
        """注销一个实现"""
        if name in self._registry:
            del self._registry[name]

class ScopeRegistry(Registry):
    """作用域注册表"""
    def get_scope(self, name: str) -> MemoryScope:
        """获取作用域实例"""
        if name not in self._registry:
            raise ValueError(f"Scope not found: {name}")
        return self._registry[name]()

class ComposerRegistry(Registry):
    """组合器注册表"""
    def get_composer(self, name: str) -> MemoryComposer:
        """获取组合器实例"""
        if name not in self._registry:
            raise ValueError(f"Composer not found: {name}")
        return self._registry[name]()

class DecomposerRegistry(Registry):
    """解析器注册表"""
    def get_decomposer(self, name: str) -> MemoryDecomposer:
        """获取解析器实例"""
        if name not in self._registry:
            raise ValueError(f"Decomposer not found: {name}")
        return self._registry[name]() 