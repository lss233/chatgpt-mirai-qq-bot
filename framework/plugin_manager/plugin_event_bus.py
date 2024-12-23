from typing import Callable, List, Type
from framework.events.event_bus import EventBus


class PluginEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self._registered_listeners: List[Callable] = []  # 记录注册过的函数

    def register(self, event_type: Type, listener: Callable):
        super().register(event_type, listener)
        self._registered_listeners.append(listener)  # 记录注册的函数

    def unregister_all(self):
        """反注册所有通过 @Event 注册的函数"""
        for listener in self._registered_listeners:
            for event_type in self._listeners:
                if listener in self._listeners[event_type]:
                    self.unregister(event_type, listener)
        self._registered_listeners.clear()  # 清空记录