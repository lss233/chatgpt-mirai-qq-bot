import asyncio

import pytest

from kirara_ai.im.adapter import IMAdapter
from kirara_ai.im.manager import IMManager
from kirara_ai.im.message import IMMessage, TextMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.implementations.blocks.im.messages import (AppendIMMessage, GetIMMessage, IMMessageToText,
                                                                   SendIMMessage, TextToIMMessage)


# 创建模拟的 IMAdapter 类
class MockIMAdapter(IMAdapter):
    async def send_message(self, message, target=None):
        return None

    def convert_to_message(self, message):
        return message.content
    
    async def start(self):
        return None
    
    async def stop(self):
        return None
    
# 创建模拟的 IMManager 类
class MockIMManager(IMManager):
    def __init__(self):
        self.adapters = {"default": MockIMAdapter(), "telegram": MockIMAdapter()}
    
    def get_adapter(self, name):
        return self.adapters.get(name)


@pytest.fixture
def container():
    """创建一个带有模拟消息的容器"""
    container = DependencyContainer()
    
    # 模拟 IMMessage
    mock_message = IMMessage(
        sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
        message_elements=[TextMessage("测试消息内容")]
    )
    container.register(IMMessage, mock_message)
    
    return container


@pytest.mark.asyncio
async def test_send_im_message_async():
    """使用 pytest-asyncio 测试发送 IM 消息块"""
    # 创建容器
    container = DependencyContainer()
    
    # 创建要发送的消息
    send_message = IMMessage(
        sender=ChatSender.get_bot_sender(),
        message_elements=[TextMessage("回复消息")]
    )
    
    mock_message = IMMessage(
        sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
        message_elements=[TextMessage("测试消息内容")]
    )
    
    # 获取事件循环
    loop = asyncio.get_event_loop()
    
    # 注册到容器
    container.register(IMAdapter, MockIMAdapter())
    container.register(IMManager, MockIMManager())
    container.register(IMMessage, mock_message)
    container.register(asyncio.AbstractEventLoop, loop)
    
    # 创建块 - 不指定适配器
    block = SendIMMessage()
    block.container = container
    
    # 执行块
    result = block.execute(msg=send_message)
    
    # 验证结果 - 应该返回空字典
    assert result == None
    
    # 创建块 - 指定适配器
    block = SendIMMessage(im_name="telegram")
    block.container = container
    
    # 执行块
    result = block.execute(msg=send_message, target="specific_user")
    
    # 验证结果
    assert result == None


def test_get_im_message(container):
    """测试获取 IM 消息块"""
    # 创建块
    block = GetIMMessage()
    block.container = container
    
    # 执行块
    result = block.execute()
    
    # 验证结果
    assert "msg" in result
    assert "sender" in result
    assert isinstance(result["msg"], IMMessage)
    assert isinstance(result["sender"], ChatSender)
    assert result["msg"].content == "测试消息内容"


def test_im_message_to_text(container):
    """测试 IMMessage 转文本块"""
    # 创建消息
    message = IMMessage(
        sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
        message_elements=[TextMessage("Hello, World!")]
    )
    
    # 创建块
    block = IMMessageToText()
    block.container = container
    
    # 执行块
    result = block.execute(msg=message)
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "Hello, World!"


def test_text_to_im_message():
    """测试文本转 IMMessage 块"""
    # 创建块 - 不分段
    block = TextToIMMessage()
    
    # 执行块
    result = block.execute(text="Hello, World!")
    
    # 验证结果
    assert "msg" in result
    assert isinstance(result["msg"], IMMessage)
    assert isinstance(result["msg"].sender, ChatSender)
    assert result["msg"].content == "Hello, World!"
    
    # 创建块 - 使用分段符
    block = TextToIMMessage(split_by="\n")
    
    # 执行块
    result = block.execute(text="Line 1\nLine 2\nLine 3")
    
    # 验证结果
    assert "msg" in result
    assert isinstance(result["msg"], IMMessage)
    assert len(result["msg"].message_elements) == 3
    assert result["msg"].message_elements[0].text == "Line 1"
    assert result["msg"].message_elements[1].text == "Line 2"
    assert result["msg"].message_elements[2].text == "Line 3"


def test_append_im_message():
    """测试补充 IMMessage 消息块"""
    # 创建基础消息
    base_message = IMMessage(
        sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
        message_elements=[TextMessage("基础消息")]
    )
    
    # 创建要追加的消息元素
    append_element = TextMessage("追加内容")
    
    # 创建块
    block = AppendIMMessage()
    
    # 执行块
    result = block.execute(base_msg=base_message, append_msg=append_element)
    
    # 验证结果
    assert "msg" in result
    assert isinstance(result["msg"], IMMessage)
    assert isinstance(result["msg"].sender, ChatSender)
    assert len(result["msg"].message_elements) == 2
    assert result["msg"].message_elements[0].text == "基础消息"
    assert result["msg"].message_elements[1].text == "追加内容" 