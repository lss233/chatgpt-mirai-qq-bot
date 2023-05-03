from typing import Tuple, Dict, Type, Optional

from .base import DrawAI
from .sdwebui import SDWebUI
from ..exceptions import NoAvailableBotException

registered_ai: Dict[str, Tuple[Type[DrawAI], Tuple]] = {}


class DrawingAIFactory:
    @staticmethod
    def create(name: Optional[str]):
        if not name:
            for key in registered_ai.keys():
                try:
                    entry = registered_ai[key]
                    return entry[0](*entry[1])
                except NoAvailableBotException:
                    pass
            return None
        if name not in registered_ai:
            raise NoAvailableBotException(name)
        entry = registered_ai[name]
        return entry[0](*entry[1])


    @staticmethod
    def register(name: str, clazz: Type[DrawAI], args: Tuple):
        registered_ai[name] = (clazz, args)
