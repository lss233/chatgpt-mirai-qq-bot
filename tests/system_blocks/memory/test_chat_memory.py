from unittest.mock import MagicMock

import pytest

from kirara_ai.im.message import IMMessage, TextMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.format.response import LLMChatResponse
from kirara_ai.memory.memory_manager import MemoryManager
from kirara_ai.memory.registry import ComposerRegistry, DecomposerRegistry, ScopeRegistry
from kirara_ai.workflow.implementations.blocks.memory.chat_memory import ChatMemoryQuery, ChatMemoryStore


# 创建模拟的 MemoryManager 类
class MockMemoryManager(MemoryManager):
    def __init__(self):
        self.config = MagicMock()
        self.config.default_scope = "member"
    
    def query(self, *args, **kwargs):
        return "系统：你是一个助手\n用户：你好\n助手：你好！有什么可以帮助你的吗？"
    
    def store(self, *args, **kwargs):
        return None
    
    def clear(self, *args, **kwargs):
        return None


# 创建模拟的 Scope 类
class MockScope:
    def __init__(self, name):
        self.name = name


# 创建模拟的 ScopeRegistry 类
class MockScopeRegistry(ScopeRegistry):
    def get_scope(self, name):
        return MockScope(name)


# 创建模拟的 Composer 类
class MockComposer:
    def compose(self, sender, messages):
        return ["memory_entry"]


# 创建模拟的 ComposerRegistry 类
class MockComposerRegistry(ComposerRegistry):
    def get_composer(self, name):
        return MockComposer()


# 创建模拟的 Decomposer 类
class MockDecomposer:
    def decompose(self, memory_entries):
        return "系统：你是一个助手\n用户：你好\n助手：你好！有什么可以帮助你的吗？"


# 创建模拟的 DecomposerRegistry 类
class MockDecomposerRegistry(DecomposerRegistry):
    def get_decomposer(self, name):
        return MockDecomposer()


@pytest.mark.asyncio
async def test_chat_memory_query_async():
    """使用 pytest-asyncio 测试聊天记忆查询块"""
    # 创建容器
    container = DependencyContainer()
    
    # 创建发送者
    chat_sender = ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User")
    
    # 注册到容器
    container.register(MemoryManager, MockMemoryManager())
    container.register(ScopeRegistry, MockScopeRegistry())
    container.register(DecomposerRegistry, MockDecomposerRegistry())
    
    # 创建块 - 默认参数
    block = ChatMemoryQuery(scope_type="member")
    block.container = container
    
    # 执行块
    result = block.execute(chat_sender=chat_sender)
    
    # 验证结果
    assert "memory_content" in result
    assert isinstance(result["memory_content"], str)
    assert "你是一个助手" in result["memory_content"]


@pytest.mark.asyncio
async def test_chat_memory_store_async():
    """使用 pytest-asyncio 测试聊天记忆存储块"""
    # 创建容器
    container = DependencyContainer()
    
    # 创建用户消息
    user_msg = IMMessage(
        sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
        message_elements=[TextMessage("新消息")]
    )
    
    # 创建 LLM 响应
    llm_resp = LLMChatResponse(
        choices=[
            {
                "message": {
                    "content": "这是 AI 的回复",
                    "role": "assistant"
                }
            }
        ],
        model="gpt-3.5-turbo",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    
    # 注册到容器
    container.register(MemoryManager, MockMemoryManager())
    container.register(ScopeRegistry, MockScopeRegistry())
    container.register(ComposerRegistry, MockComposerRegistry())
    
    # 创建块
    block = ChatMemoryStore(scope_type="member")
    block.container = container
    
    # 执行块 - 存储用户消息
    result = block.execute(user_msg=user_msg)
    
    # 验证结果
    assert result == {}
    
    # 执行块 - 存储 LLM 响应
    result = block.execute(
        user_msg=user_msg,
        llm_resp=llm_resp
    )
    
    # 验证结果
    assert result == {} 