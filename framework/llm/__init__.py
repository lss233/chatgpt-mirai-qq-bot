from typing import Type, Dict, Tuple


from .llm import Llm
from ..exceptions import BotTypeNotFoundException

from .openai.api import ChatGPTAPIAdapter
from .openai.web import ChatGPTWebAdapter
from .claude.slack import ClaudeInSlackAdapter
from .google.bard import BardAdapter
from .quora.poe_web import BotType as PoeBotType, PoeAdapter
from .thudm.chatglm_6b import ChatGLM6BAdapter
from .baidu.yiyan import YiyanAdapter
from .microsoft.bing import BingAdapter

registered_ai: Dict[str, Tuple[Type[Llm], Tuple]] = {}


class LlmFactory:

    @staticmethod
    def create(name: str, session_id: str, **kwargs) -> Llm:
        if name not in registered_ai:
            raise BotTypeNotFoundException(name)
        entry = registered_ai[name]
        return entry[0](*((session_id, ) + entry[1]))

    @staticmethod
    def register(name: str, clazz: Type[Llm], args: Tuple):
        registered_ai[name] = (clazz, args)
        clazz.register()
