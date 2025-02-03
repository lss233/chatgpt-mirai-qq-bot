import pytest
from unittest.mock import MagicMock
from framework.ioc.container import DependencyContainer
from framework.workflow.implementations.factories.game_factory import GameWorkflowFactory
from framework.workflow.implementations.factories.system_factory import SystemWorkflowFactory

@pytest.fixture
def container():
    return MagicMock(spec=DependencyContainer)

def test_game_dice_workflow(container):
    """测试骰子游戏工作流创建"""
    workflow = GameWorkflowFactory.create_dice_workflow(container)
    
    # 验证工作流结构
    assert workflow.name == "dice_workflow"
    assert len(workflow.blocks) == 3  # GetIMMessage -> DiceRoll -> SendIMMessage
    
    # 验证连接
    assert len(workflow.wires) == 2  # 两个连接

def test_game_gacha_workflow(container):
    """测试抽卡游戏工作流创建"""
    workflow = GameWorkflowFactory.create_gacha_workflow(container)
    
    # 验证工作流结构
    assert workflow.name == "gacha_workflow"
    assert len(workflow.blocks) == 3  # GetIMMessage -> GachaSimulator -> SendIMMessage
    
    # 验证连接
    assert len(workflow.wires) == 2  # 两个连接

def test_system_help_workflow(container):
    """测试帮助信息工作流创建"""
    workflow = SystemWorkflowFactory.create_help_workflow(container)
    
    # 验证工作流结构
    assert workflow.name == "help_workflow"
    assert len(workflow.blocks) == 2  # GenerateHelp -> SendIMMessage
    
    # 验证连接
    assert len(workflow.wires) == 1  # 一个连接 