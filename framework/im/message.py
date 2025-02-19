import base64
import os
from abc import ABC, abstractmethod
from typing import List, Optional

from framework.im.sender import ChatSender


# 定义消息元素的基类
class MessageElement(ABC):
    @abstractmethod
    def to_dict(self):
        pass

    @abstractmethod
    def to_plain(self):
        pass


# 定义文本消息元素
class TextMessage(MessageElement):
    def __init__(self, text: str):
        self.text = text

    def to_dict(self):
        return {"type": "text", "text": self.text}

    def to_plain(self):
        return self.text

    def __repr__(self):
        return f"TextMessage(text={self.text})"


# 定义媒体消息的基类
class MediaMessage(MessageElement):

    def __init__(
        self,
        url: Optional[str] = None,
        path: Optional[str] = None,
        data: Optional[bytes] = None,
        format: Optional[str] = None,
    ):
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


# 定义语音消息
class VoiceMessage(MediaMessage):
    def to_dict(self):
        return {
            "type": "voice",
            "url": self.url,
            "path": self.path,
            "data": base64.b64encode(self.data).decode() if self.data else None,
            "format": self.format,
        }

    def to_plain(self):
        return "[VoiceMessage]"


# 定义图片消息
class ImageMessage(MediaMessage):
    def to_dict(self):
        return {
            "type": "image",
            "url": self.url,
            "path": self.path,
            "data": base64.b64encode(self.data).decode() if self.data else None,
            "format": self.format,
        }

    def to_plain(self):
        return "[ImageMessage]"

    def __repr__(self):
        return f"ImageMessage(url={self.url}, path={self.path}, format={self.format})"

# 定义@消息元素
# :deprecated
class AtElement(MessageElement):

    def __init__(self, user_id: str, nickname: str = ""):
        self.user_id = user_id
        self.nickname = nickname

    def to_dict(self):
        return {"type": "at", "data": {"qq": self.user_id, "nickname": self.nickname}}

    def to_plain(self):
        return f"@{self.nickname or self.user_id}"

    def __repr__(self):
        return f"AtElement(user_id={self.user_id}, nickname={self.nickname})"

# 定义@消息元素
class MentionElement(MessageElement):
    def __init__(self, target: ChatSender):
        self.target = target

    def to_dict(self):
        return {"type": "mention", "data": {"target": self.target}}

    def to_plain(self):
        return f"@{self.target.display_name or self.target.user_id}"
    
    def __repr__(self):
        return f"MentionElement(target={self.target})"

# 定义回复消息元素
class ReplyElement(MessageElement):

    def __init__(self, message_id: str):
        self.message_id = message_id

    def to_dict(self):

        return {"type": "reply", "data": {"id": self.message_id}}

    def to_plain(self):
        return f"[Reply:{self.message_id}]"

    def __repr__(self):
        return f"ReplyElement(message_id={self.message_id})"


# 定义文件消息元素
class FileElement(MediaMessage):

    def to_dict(self):
        return {
            "type": "file",
            "url": self.url,
            "path": self.path,
            "data": base64.b64encode(self.data).decode() if self.data else None,
            "format": self.format,
        }

    def to_plain(self):
        return f"[File:{self.path or self.url or 'unnamed'}]"

    def __repr__(self):
        return f"FileElement(url={self.url}, path={self.path}, format={self.format})"


# 定义JSON消息元素
class JsonElement(MessageElement):

    def __init__(self, data: str):
        self.data = data

    def to_dict(self):
        return {"type": "json", "data": {"data": self.data}}

    def to_plain(self):
        return "[JSON Message]"

    def __repr__(self):
        return f"JsonElement(data={self.data})"


# 定义表情消息元素
class FaceElement(MessageElement):

    def __init__(self, face_id: str):
        self.face_id = face_id

    def to_dict(self):

        return {"type": "face", "data": {"id": self.face_id}}

    def to_plain(self):
        return f"[Face:{self.face_id}]"

    def __repr__(self):
        return f"FaceElement(face_id={self.face_id})"


# 定义视频消息元素
class VideoElement(MessageElement):
    def __init__(self, file: str):
        self.file = file

    def to_dict(self):

        return {"type": "video", "data": {"file": self.file}}

    def to_plain(self):
        return "[Video Message]"

    def __repr__(self):
        return f"VideoElement(file={self.file})"


# 定义消息类
class IMMessage:
    """
    IM消息类，用于表示一条完整的消息。
    包含发送者信息和消息元素列表。

    Attributes:
        sender: 发送者标识
        message_elements: 消息元素列表,可以包含文本、图片、语音等
        raw_message: 原始消息数据
        content: 消息的纯文本内容
        images: 消息中的图片列表
        voices: 消息中的语音列表
    """

    sender: ChatSender
    message_elements: List[MessageElement]
    raw_message: Optional[dict]

    def __repr__(self):
        return f"IMMessage(sender={self.sender}, message_elements={self.message_elements}, raw_message={self.raw_message})"

    @property
    def content(self) -> str:
        """获取消息的纯文本内容"""
        return "".join([element.to_plain() for element in self.message_elements])

    @property
    def images(self) -> List[ImageMessage]:
        """获取消息中的所有图片"""
        return [
            element
            for element in self.message_elements
            if isinstance(element, ImageMessage)
        ]

    @property
    def voices(self) -> List[VoiceMessage]:
        """获取消息中的所有语音"""
        return [
            element
            for element in self.message_elements
            if isinstance(element, VoiceMessage)
        ]

    def __init__(
        self,
        sender: ChatSender,
        message_elements: List[MessageElement],
        raw_message: dict = None,
    ):
        self.sender = sender
        self.message_elements = message_elements
        self.raw_message = raw_message

    def to_dict(self):
        return {
            "sender": self.sender,
            "message_elements": [
                element.to_dict() for element in self.message_elements
            ],
            "plain_text": "".join(
                [element.to_plain() for element in self.message_elements]
            ),
            "raw_message": self.raw_message,
        }


# 示例用法
if __name__ == "__main__":
    # 创建消息元素
    text_element = TextMessage("Hello, World!")
    voice_element = VoiceMessage("https://example.com/voice.mp3", 120)
    image_element = ImageMessage("https://example.com/image.jpg", 800, 600)

    # 创建消息对象
    message = IMMessage(
        sender=ChatSender.from_c2c_chat("user123"),
        message_elements=[text_element, voice_element, image_element],
        raw_message={"platform": "example_chat", "timestamp": "2023-10-01T12:00:00Z"},
    )

    # 转换为字典格式
    message_dict = message.to_dict()
    print(message_dict)
