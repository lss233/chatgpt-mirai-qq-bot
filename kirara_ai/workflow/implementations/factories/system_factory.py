from kirara_ai.workflow.core.workflow.builder import WorkflowBuilder
from kirara_ai.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage
from kirara_ai.workflow.implementations.blocks.memory.clear_memory import ClearMemory
from kirara_ai.workflow.implementations.blocks.system.help import GenerateHelp


class SystemWorkflowFactory:
    """系统相关工作流工厂"""

    @staticmethod
    def create_help_workflow() -> WorkflowBuilder:
        """创建帮助信息工作流"""
        return WorkflowBuilder("帮助信息").use(GenerateHelp).chain(SendIMMessage)

    @staticmethod
    def create_clear_memory_workflow() -> WorkflowBuilder:
        """创建清空记忆工作流"""
        return (
            WorkflowBuilder("清空记忆")
            .use(GetIMMessage)
            .parallel(
                [
                    (ClearMemory, {"scope_type": "group"}),
                    (ClearMemory, {"scope_type": "member"}),
                ]
            )
            .chain(SendIMMessage)
        )
