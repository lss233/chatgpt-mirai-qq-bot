from abc import ABC, abstractmethod
from typing import Any
from framework.im.message import IMMessage
from framework.llm.llm_manager import LLMManager
from framework.llm.llm_registry import LLMBackendRegistry

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
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass