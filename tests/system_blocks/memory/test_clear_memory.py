from unittest.mock import MagicMock

import pytest

from kirara_ai.im.message import IMMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.memory.memory_manager import MemoryManager
from kirara_ai.memory.registry import ComposerRegistry, DecomposerRegistry, ScopeRegistry
from kirara_ai.workflow.implementations.blocks.memory.clear_memory import ClearMemory


# 创建模拟的 MemoryManager 类
class MockMemoryManager(MemoryManager):
    def __init__(self):
        self.config = MagicMock()
        self.config.default_scope = "member"
        self.memories = {}
    
    def clear_memory(self, *args, **kwargs):
        return None


# 创建模拟的 Scope 类
class MockScope:
    def __init__(self, name):
        self.name = name
        
    def get_scope_key(self, sender: ChatSender):
        return sender.user_id


# 创建模拟的 ScopeRegistry 类
class MockScopeRegistry(ScopeRegistry):
    def get_scope(self, name):
        return MockScope(name)


@pytest.mark.asyncio
async def test_clear_memory_async():
    """使用 pytest-asyncio 测试清除记忆块"""
    # 创建容器
    container = DependencyContainer()
    
    # 创建发送者
    chat_sender = ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User")
    
    # 注册到容器
    container.register(MemoryManager, MockMemoryManager())
    container.register(ScopeRegistry, MockScopeRegistry())
    container.register(ComposerRegistry, MagicMock(spec=ComposerRegistry))
    container.register(DecomposerRegistry, MagicMock(spec=DecomposerRegistry))
    
    # 创建块
    block = ClearMemory(scope_type="member")
    block.container = container
    
    # 执行块 - 使用默认发送者
    result = block.execute(chat_sender=chat_sender)
    
    # 验证结果
    assert "response" in result
    assert isinstance(result["response"], IMMessage)
    assert "已清空" in result["response"].content or "清除" in result["response"].content
    
    # 执行块 - 使用自定义发送者
    custom_sender = ChatSender.from_c2c_chat(user_id="custom_user", display_name="Custom User")
    result = block.execute(chat_sender=custom_sender)
    
    # 验证结果
    assert "response" in result
    assert isinstance(result["response"], IMMessage)