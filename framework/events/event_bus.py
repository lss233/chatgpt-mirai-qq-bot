import inspect
from typing import Callable, Type, Dict, List

class EventBus:
    def __init__(self):
        self._listeners: Dict[Type, List[Callable]] = {}

    def register(self, event_type: Type, listener: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unregister(self, event_type: Type, listener: Callable):
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)

    def post(self, event):
        event_type = type(event)
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                listener(event)

def Event(event_bus: EventBus):
    def decorator(func: Callable):
        # 获取函数的参数签名
        signature = inspect.signature(func)
        params = list(signature.parameters.values())
        
        # 假设第一个参数是事件类型
        if len(params) == 0:
            raise ValueError("Listener function must have at least one parameter")
        
        event_type = params[0].annotation
        
        # 如果没有指定类型注解，抛出异常
        if event_type == inspect.Parameter.empty:
            raise ValueError("Listener function must have an annotated first parameter")
        
        # 注册监听器
        event_bus.register(event_type, func)
        
        return func
    return decorator