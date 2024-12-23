import inspect
from typing import Callable

from framework.events.event_bus import EventBus


def Event(event_bus: EventBus):
    def decorator(func: Callable):
        # 获取函数的参数签名
        signature = inspect.signature(func)
        params = list(signature.parameters.values())

        # 假设第一个参数是事件类型
        if not params:
            raise ValueError("Listener function must have at least one parameter")

        event_type = params[0].annotation

        # 如果没有指定类型注解，抛出异常
        if event_type == inspect.Parameter.empty:
            raise ValueError("Listener function must have an annotated first parameter")

        # 注册监听器
        event_bus.register(event_type, func)

        return func

    return decorator