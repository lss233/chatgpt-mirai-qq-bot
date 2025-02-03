from framework.workflow_executor.builder import WorkflowBuilder
from framework.workflow_executor.workflow import Workflow
from framework.ioc.container import DependencyContainer
from framework.workflows.blocks.system.help import GenerateHelp
from framework.workflows.blocks.im.messages import SendIMMessage

class SystemWorkflowFactory:
    """系统相关工作流工厂"""
    
    @staticmethod
    def create_help_workflow(container: DependencyContainer) -> Workflow:
        """创建帮助信息工作流"""
        return (WorkflowBuilder("help_workflow", container)
            .use(GenerateHelp)
            .chain(SendIMMessage)
            .build())