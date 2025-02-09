from framework.workflow.core.workflow.builder import WorkflowBuilder
from framework.workflow.core.workflow import Workflow
from framework.ioc.container import DependencyContainer
from framework.workflow.implementations.blocks.system.help import GenerateHelp
from framework.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage
from framework.workflow.implementations.blocks.memory.clear_memory import ClearMemory

class SystemWorkflowFactory:
    """系统相关工作流工厂"""
    
    @staticmethod
    def create_help_workflow() -> WorkflowBuilder:
        """创建帮助信息工作流"""
        return (WorkflowBuilder("help_workflow")
            .use(GenerateHelp)
            .chain(SendIMMessage))
            
    @staticmethod
    def create_clear_memory_workflow() -> WorkflowBuilder:
        """创建清空记忆工作流"""
        return (WorkflowBuilder("clear_memory_workflow")
            .use(GetIMMessage)
            .chain(ClearMemory)
            .chain(SendIMMessage))