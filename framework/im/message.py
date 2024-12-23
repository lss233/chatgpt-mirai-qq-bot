from typing import List, Optional
from abc import ABC, abstractmethod
import os
import base64

# 定义消息元素的基类
class MessageElement(ABC):
    @abstractmethod
    def to_dict(self):
        pass

# 定义文本消息元素
class TextMessage(MessageElement):
    def __init__(self, text: str):
        self.text = text

    def to_dict(self):
        return {"type": "text", "text": self.text}

# 定义媒体消息的基类
class MediaMessage(ABC):
    def __init__(self, url: Optional[str] = None, path: Optional[str] = None, data: Optional[bytes] = None, format: Optional[str] = None):
        self.url = url
        self.path = path
        self.data = data
        self.format = format

        # 根据传入的参数计算其他属性
        if url:
            self._from_url(url)
        elif path:
            self._from_path(path)
        elif data and format:
            self._from_data(data, format)
        else:
            raise ValueError("Must provide either url, path, or data + format.")

    def _from_url(self, url: str):
        """从 URL 计算其他属性"""
        self.url = url
        self.path = None
        self.data = None
        self.format = url.split(".")[-1] if "." in url else None

    def _from_path(self, path: str):
        """从文件路径计算其他属性"""
        self.path = path
        self.url = None
        self.data = None
        self.format = os.path.splitext(path)[-1].lstrip(".")

    def _from_data(self, data: bytes, format: str):
        """从数据和格式计算其他属性"""
        self.data = data
        self.format = format
        self.url = None
        self.path = None

    @abstractmethod
    def to_dict(self):
        pass

# 定义语音消息
class VoiceMessage(MediaMessage):
    def to_dict(self):
        return {
            "type": "voice",
            "url": self.url,
            "path": self.path,
            "data": base64.b64encode(self.data).decode() if self.data else None,
            "format": self.format
        }

# 定义图片消息
class ImageMessage(MediaMessage):
    def to_dict(self):
        return {
            "type": "image",
            "url": self.url,
            "path": self.path,
            "data": base64.b64encode(self.data).decode() if self.data else None,
            "format": self.format
        }

# 定义消息类
class Message:
    def __init__(self, sender: str, message_elements: List[MessageElement], raw_message: dict = None):
        self.sender = sender
        self.message_elements = message_elements
        self.raw_message = raw_message

    def to_dict(self):
        return {
            "sender": self.sender,
            "message_elements": [element.to_dict() for element in self.message_elements],
            "raw_message": self.raw_message
        }

# 示例用法
if __name__ == "__main__":
    # 创建消息元素
    text_element = TextMessage("Hello, World!")
    voice_element = VoiceMessage("https://example.com/voice.mp3", 120)
    image_element = ImageMessage("https://example.com/image.jpg", 800, 600)

    # 创建消息对象
    message = Message(
        sender="user123",
        message_elements=[text_element, voice_element, image_element],
        raw_message={"platform": "example_chat", "timestamp": "2023-10-01T12:00:00Z"}
    )

    # 转换为字典格式
    message_dict = message.to_dict()
    print(message_dict)