from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol

from pydantic import BaseModel
from typing_extensions import runtime_checkable

from kirara_ai.im.message import IMMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.llm.llm_manager import LLMManager

from .profile import UserProfile


class BotStatus(BaseModel):
    """
    机器人状态
    """

    username: str
    avatar_url: str

@runtime_checkable
class EditStateAdapter(Protocol):
    """
    编辑状态适配器接口，定义了如何设置或取消对话的编辑状态
    """

    async def set_chat_editing_state(
        self, chat_sender: ChatSender, is_editing: bool = True
    ):
        """
        设置或取消对话的编辑状态
        :param chat_sender: 对话的发送者
        :param is_editing: True 表示正在编辑，False 表示取消编辑状态
        """


@runtime_checkable
class UserProfileAdapter(Protocol):
    """
    用户资料查询适配器接口，定义了如何获取用户资料
    """

    async def query_user_profile(self, chat_sender: ChatSender) -> UserProfile:
        """
        查询用户资料
        :param chat_sender: 用户的聊天发送者信息
        :return: 用户资料
        """

@runtime_checkable
class BotProfileAdapter(Protocol):
    """
    支持获取当前适配器对应的机器人资料
    """

    async def get_bot_profile(self) -> Optional[UserProfile]:
        """
        获取机器人资料
        :return: 机器人资料
        """

class IMAdapter(ABC):
    """
    通用的 IM 适配器接口，定义了如何将不同平台的原始消息转换为 Message 对象。
    """

    llm_manager: LLMManager

    @abstractmethod
    def convert_to_message(self, raw_message: Any) -> IMMessage:
        """
        将平台的原始消息转换为 Message 对象。
        :param raw_message: 平台的原始消息对象。
        :return: 转换后的 Message 对象。
        """

    @abstractmethod
    async def send_message(self, message: IMMessage, recipient: Any):
        """
        发送消息到 IM 平台。
        :param message: 要发送的消息对象。
        :param recipient: 接收消息的目标对象，可以是用户ID、用户对象、群组ID等，具体由各平台实现决定。
        """

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass
