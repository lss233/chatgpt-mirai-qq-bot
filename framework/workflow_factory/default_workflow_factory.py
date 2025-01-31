from framework.ioc.container import DependencyContainer
from framework.workflow_executor.workflow import Workflow

class DefaultWorkflowFactory:
    def create_workflow(self, container: DependencyContainer) -> Workflow:
        # Create and return a default workflow implementation
        from framework.workflow_factory.default_workflow import DefaultWorkflow
        return DefaultWorkflow(container) 