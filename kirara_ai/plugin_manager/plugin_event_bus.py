from typing import Callable, List, Type

from kirara_ai.events.event_bus import EventBus


class PluginEventBus:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._registered_listeners: List[Callable] = []  # 记录注册过的函数

    def register(self, event_type: Type, listener: Callable):
        self._event_bus.register(event_type, listener)
        self._registered_listeners.append(listener)  # 记录注册的函数

    def unregister(self, event_type: Type, listener: Callable):
        self._event_bus.unregister(event_type, listener)

    def post(self, event):
        self._event_bus.post(event)

    def unregister_all(self):
        """反注册所有通过 @Event 注册的函数"""
        for listener in self._registered_listeners:
            for event_type in self._event_bus._listeners:
                if listener in self._event_bus._listeners[event_type]:
                    self._event_bus.unregister(event_type, listener)
        self._registered_listeners.clear()  # 清空记录