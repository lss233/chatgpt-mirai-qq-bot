from typing import Callable, Optional

from graia.ariadne.message import MessageChain

from framework.conversation import ConversationContext
from framework.messages import ImageElement
from framework.tts.tts import TTSResponse


class Request:
    session_id: str
    user_id: Optional[str]
    group_id: Optional[str]
    nickname: Optional[str]
    message: MessageChain
    conversation_context: Optional[ConversationContext]
    is_manager: bool = False

    @property
    def text(self):
        return str(self.message)


class Response:
    __respond_func: Callable

    body: Optional[MessageChain]

    def __init__(self, respond_func: Callable, body: Optional[MessageChain] = None):
        self.__respond_func = respond_func
        self.body = body

    async def send(self, chain: MessageChain = None, text: str = None, voice: TTSResponse = None,
                   image: ImageElement = None):
        return await self.__respond_func(chain=chain, text=text, voice=voice, image=image)
