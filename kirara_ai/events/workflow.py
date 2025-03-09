from typing import Any, Dict

from kirara_ai.workflow.core.execution.executor import WorkflowExecutor
from kirara_ai.workflow.core.workflow.base import Workflow


class WorkflowExecutionBegin:
    def __init__(self, workflow: Workflow, executor: WorkflowExecutor):
        self.workflow = workflow
        self.executor = executor

    def __repr__(self):
        return f"{self.__class__.__name__}(workflow={self.workflow}, executor={self.executor})"
    

class WorkflowExecutionEnd:
    def __init__(self, workflow: Workflow, executor: WorkflowExecutor, results: Dict[str, Any]):
        self.workflow = workflow
        self.executor = executor
        self.results = results


