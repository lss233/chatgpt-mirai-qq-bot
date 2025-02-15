from abc import ABC, abstractmethod
from typing import Any, Protocol
from typing_extensions import runtime_checkable
from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from framework.llm.llm_manager import LLMManager
from .profile import UserProfile

@runtime_checkable
class EditStateAdapter(Protocol):
    """
    编辑状态适配器接口，定义了如何设置或取消对话的编辑状态
    """
    async def set_chat_editing_state(self, chat_sender: ChatSender, is_editing: bool = True):
        """
        设置或取消对话的编辑状态
        :param chat_sender: 对话的发送者
        :param is_editing: True 表示正在编辑，False 表示取消编辑状态
        """
        pass

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
        pass

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
        pass

    @abstractmethod
    async def send_message(self, message: IMMessage, recipient: Any):
        """
        发送消息到 IM 平台。
        :param message: 要发送的消息对象。
        :param recipient: 接收消息的目标对象，可以是用户ID、用户对象、群组ID等，具体由各平台实现决定。
        """
        pass

    @abstractmethod
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass