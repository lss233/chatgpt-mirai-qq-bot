from framework.workflow.core.workflow.registry import WorkflowRegistry
from framework.workflow.implementations.factories.game_factory import GameWorkflowFactory
from framework.workflow.implementations.factories.system_factory import SystemWorkflowFactory
from framework.workflow.implementations.factories.default_factory import DefaultWorkflowFactory

def register_system_workflows(registry: WorkflowRegistry):
    """注册系统自带的工作流"""
    
    # 游戏相关工作流
    registry.register_preset_workflow("game", "dice", GameWorkflowFactory.create_dice_workflow())
    registry.register_preset_workflow("game", "gacha", GameWorkflowFactory.create_gacha_workflow())
    
    # 系统相关工作流
    registry.register_preset_workflow("system", "help", SystemWorkflowFactory.create_help_workflow())
    registry.register_preset_workflow("system", "admin", SystemWorkflowFactory.create_help_workflow())
    registry.register_preset_workflow("system", "status", SystemWorkflowFactory.create_help_workflow())
    registry.register_preset_workflow("system", "settings", SystemWorkflowFactory.create_help_workflow())
    registry.register_preset_workflow("system", "clear_memory", SystemWorkflowFactory.create_clear_memory_workflow())
    
    # 聊天相关工作流
    registry.register_preset_workflow("chat", "normal", DefaultWorkflowFactory.create_default_workflow())
    registry.register_preset_workflow("chat", "creative", DefaultWorkflowFactory.create_default_workflow())
    registry.register_preset_workflow("chat", "roleplay", DefaultWorkflowFactory.create_default_workflow()) 