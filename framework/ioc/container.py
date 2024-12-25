import contextvars
from functools import wraps
from inspect import signature

# 使用 contextvars 实现线程和异步安全的上下文管理
current_container = contextvars.ContextVar("current_container", default=None)

class DependencyContainer:
    def __init__(self, parent=None):
        self.parent = parent  # 父容器，用于支持作用域嵌套
        self.registry = {}  # 当前容器的注册表

    def register(self, key, value):
        self.registry[key] = value

    def resolve(self, key):
        # 先在当前容器中查找，如果没有则递归查找父容器
        if key in self.registry:
            return self.registry[key]
        elif self.parent:
            return self.parent.resolve(key)
        else:
            raise KeyError(f"Dependency {key} not found.")

    def scoped(self):
        """创建一个新的作用域容器"""
        new_container = ScopedContainer(self)
        
        if DependencyContainer in self.registry:
            new_container.registry[DependencyContainer] = new_container
            new_container.registry[ScopedContainer] = new_container
        return new_container

class ScopedContainer(DependencyContainer):
    def __init__(self, parent):
        super().__init__(parent)

    def __enter__(self):
        # 将当前容器设置为新的作用域容器
        self.token = current_container.set(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # 恢复之前的容器
        current_container.reset(self.token)