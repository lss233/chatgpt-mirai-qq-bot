from typing import Callable, Optional

from graia.ariadne.message.chain import MessageChain

from framework.conversation import ConversationContext
from framework.messages import ImageElement
from framework.tts.tts import TTSResponse


class Request:
    session_id: str
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    nickname: Optional[str] = None
    message: MessageChain
    conversation_context: Optional[ConversationContext] = None
    is_manager: bool = False

    @property
    def text(self):
        return str(self.message)


class Response:
    __respond_func: Callable

    chain: Optional[MessageChain]
    text: Optional[str]
    voice: Optional[TTSResponse]
    image: Optional[ImageElement]

    def __init__(self, respond_func: Callable):
        self.   __respond_func = respond_func

    async def send(self, chain: MessageChain = None, text: str = None, voice: TTSResponse = None,
                   image: ImageElement = None):
        return await self.__respond_func(chain=chain, text=text, voice=voice, image=image)

    @property
    def has_content(self):
        return not self.chain or not self.image or not self.text or not self.voice
