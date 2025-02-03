from framework.ioc.container import DependencyContainer
from framework.workflow.core.workflow import Workflow

class DefaultWorkflowFactory:
    """
    构建默认的聊天工作流，提供基本的聊天 bot 能力。
    """
    def create_workflow(self, container: DependencyContainer) -> Workflow:
        # Create and return a default workflow implementation
        from framework.workflow.implementations.workflows.default.workflow import create_default_workflow
        workflow = create_default_workflow(container)
        return workflow
