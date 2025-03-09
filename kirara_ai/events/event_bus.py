from typing import Callable, Dict, List, Type

from kirara_ai.logger import get_logger

logger = get_logger("EventBus")

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
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in listener {listener.__name__}: {e}", exc_info=True)
