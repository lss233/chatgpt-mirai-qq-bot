from kirara_ai.workflow.core.workflow.registry import WorkflowRegistry
from kirara_ai.workflow.implementations.factories.default_factory import DefaultWorkflowFactory
from kirara_ai.workflow.implementations.factories.game_factory import GameWorkflowFactory
from kirara_ai.workflow.implementations.factories.system_factory import SystemWorkflowFactory


def register_system_workflows(registry: WorkflowRegistry):
    """注册系统自带的工作流"""

    # 游戏相关工作流
    registry.register_preset_workflow(
        "game", "dice", GameWorkflowFactory.create_dice_workflow()
    )
    registry.register_preset_workflow(
        "game", "gacha", GameWorkflowFactory.create_gacha_workflow()
    )

    # 系统相关工作流
    registry.register_preset_workflow(
        "system", "help", SystemWorkflowFactory.create_help_workflow()
    )
    registry.register_preset_workflow(
        "system", "clear_memory", SystemWorkflowFactory.create_clear_memory_workflow()
    )

    # 聊天相关工作流
    registry.register_preset_workflow(
        "chat", "normal", DefaultWorkflowFactory.create_default_workflow()
    )
    registry.register_preset_workflow(
        "chat", "creative", DefaultWorkflowFactory.create_default_workflow()
    )
    registry.register_preset_workflow(
        "chat", "roleplay", DefaultWorkflowFactory.create_default_workflow()
    )
