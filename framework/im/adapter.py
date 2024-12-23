from abc import ABC, abstractmethod
from typing import Any
from framework.im.message import Message

class IMAdapter(ABC):
    """
    通用的 IM 适配器接口，定义了如何将不同平台的原始消息转换为 Message 对象。
    """

    @abstractmethod
    def convert_to_message(self, raw_message: Any) -> Message:
        """
        将平台的原始消息转换为 Message 对象。
        :param raw_message: 平台的原始消息对象。
        :return: 转换后的 Message 对象。
        """
        pass
    @abstractmethod
    def run(self):
        pass