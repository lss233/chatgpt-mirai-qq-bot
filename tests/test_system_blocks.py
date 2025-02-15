import pytest
from unittest.mock import MagicMock
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry
from framework.workflow.core.dispatch.rule import PrefixMatchRule
from framework.workflow.implementations.blocks.system.help import GenerateHelp
from framework.ioc.container import DependencyContainer
from framework.im.message import IMMessage

@pytest.fixture
def container():
    container = MagicMock(spec=DependencyContainer)
    registry = MagicMock(spec=DispatchRuleRegistry)
    container.resolve.return_value = registry
    return container, registry

def test_generate_help_basic(container):
    """测试基本的帮助信息生成"""
    container, registry = container
    
    # 创建工作流工厂 mock
    system_factory = MagicMock()
    system_factory.__class__.__name__ = "SystemWorkflowFactory"
    
    chat_factory = MagicMock()
    chat_factory.__class__.__name__ = "ChatWorkflowFactory"
    
    # 模拟一些调度规则
    rule1 = MagicMock(spec=PrefixMatchRule)
    rule1.prefix = "/help"
    rule1.description = "显示帮助信息"
    rule1.workflow_factory = system_factory
    
    rule2 = MagicMock(spec=PrefixMatchRule)
    rule2.prefix = "/chat"
    rule2.description = "开始聊天"
    rule2.workflow_factory = chat_factory
    
    registry.get_all_rules.return_value = [rule1, rule2]
    registry.get_active_rules.return_value = [rule1, rule2]
    block = GenerateHelp()
    block.container = container
    result = block.execute()
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert response.sender == "<@bot>"
    
    help_text = response.content
    
    # 检查帮助文本格式
    assert "机器人命令帮助" in help_text
    assert "/help" in help_text
    assert "/chat" in help_text
    assert "显示帮助信息" in help_text
    assert "开始聊天" in help_text

def test_generate_help_empty(container):
    """测试没有规则时的帮助信息生成"""
    container, registry = container
    registry.get_all_rules.return_value = []
    
    block = GenerateHelp()
    block.container = container
    result = block.execute()
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    help_text = response.content

    
    # 检查基本格式
    assert "机器人命令帮助" in help_text

def test_generate_help_no_description(container):
    """测试规则没有描述时的处理"""
    container, registry = container
    
    # 创建工作流工厂 mock
    test_factory = MagicMock()
    test_factory.__class__.__name__ = "TestWorkflowFactory"
    
    rule = MagicMock(spec=PrefixMatchRule)
    rule.prefix = "/test"
    rule.workflow_factory = test_factory
    # 不设置 description
    
    registry.get_all_rules.return_value = [rule]
    
    block = GenerateHelp()
    block.container = container
    result = block.execute()
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    help_text = response.content

    
    # 不应该包含没有描述的命令
    assert "/test" not in help_text 