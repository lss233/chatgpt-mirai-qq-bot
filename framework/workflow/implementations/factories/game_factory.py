from framework.ioc.container import DependencyContainer
from framework.workflow.core.workflow.builder import WorkflowBuilder
from framework.workflow.core.workflow import Workflow
from framework.workflow.implementations.blocks.game.dice import DiceRoll
from framework.workflow.implementations.blocks.game.gacha import GachaSimulator
from framework.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage

class GameWorkflowFactory:
    """游戏相关工作流工厂"""
    
    @staticmethod
    def create_dice_workflow() -> WorkflowBuilder:
        """创建骰子游戏工作流"""
        return (WorkflowBuilder("dice_workflow")
            .use(GetIMMessage)
            .chain(DiceRoll)
            .chain(SendIMMessage))
            
    @staticmethod
    def create_gacha_workflow() -> WorkflowBuilder:
        """创建抽卡游戏工作流"""
        return (WorkflowBuilder("gacha_workflow")
            .use(GetIMMessage)
            .chain(GachaSimulator)
            .chain(SendIMMessage)) 