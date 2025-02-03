from framework.workflow_executor.builder import WorkflowBuilder
from framework.workflow_executor.workflow import Workflow
from framework.ioc.container import DependencyContainer
from framework.workflows.blocks.game.dice import DiceRoll
from framework.workflows.blocks.game.gacha import GachaSimulator
from framework.workflows.blocks.im.messages import GetIMMessage, SendIMMessage

class GameWorkflowFactory:
    """游戏相关工作流工厂"""
    
    @staticmethod
    def create_dice_workflow(container: DependencyContainer) -> Workflow:
        """创建骰子游戏工作流"""
        return (WorkflowBuilder("dice_workflow", container)
            .use(GetIMMessage)
            .chain(DiceRoll)
            .chain(SendIMMessage)
            .build())
            
    @staticmethod
    def create_gacha_workflow(container: DependencyContainer) -> Workflow:
        """创建抽卡游戏工作流"""
        return (WorkflowBuilder("gacha_workflow", container)
            .use(GetIMMessage)
            .chain(GachaSimulator)
            .chain(SendIMMessage)
            .build()) 