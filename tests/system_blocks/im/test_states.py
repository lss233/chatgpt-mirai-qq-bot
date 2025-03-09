import asyncio

import pytest

from kirara_ai.im.adapter import EditStateAdapter, IMAdapter
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.implementations.blocks.im.states import ToggleEditState


class MockAdapter(IMAdapter, EditStateAdapter):
    async def set_chat_editing_state(self, *args, **kwargs):
        return None

@pytest.mark.asyncio
async def test_toggle_edit_state_async():
    """使用 pytest-asyncio 测试切换编辑状态块"""
    # 创建容器
    container = DependencyContainer()
    
    # 创建发送者
    sender = ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User")

    loop = asyncio.get_event_loop()
    
    # 注册到容器
    container.register(IMAdapter, MockAdapter)
    container.register(asyncio.AbstractEventLoop, loop)
    
    # 创建块 - 默认参数
    block = ToggleEditState(is_editing=True)
    block.container = container
    
    # 执行块 - 传入发送者
    result = block.execute(sender=sender)
    
    # 验证结果 - 异步方法应该返回空字典
    assert result == {}