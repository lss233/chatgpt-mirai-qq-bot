from typing import Any, Dict, Type, TypeVar, Optional
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output
from framework.workflow.core.execution.executor import WorkflowExecutor

T = TypeVar('T')

class SetVariableBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {
            "name": Input("name", "变量名", str, "变量名"),
            "value": Input("value", "变量值", Any, "变量值")
        }
        outputs = {}  # 这个 block 不需要输出
        super().__init__("set_variable", inputs, outputs)
        self.container = container

    def execute(self, name: str, value: Any) -> Dict[str, Any]:
        executor = self.container.resolve(WorkflowExecutor)
        executor.set_variable(name, value)
        return {}

class GetVariableBlock(Block):
    def __init__(self, container: DependencyContainer, var_type: Type[T]):
        inputs = {
            "name": Input("name", "变量名", str, "变量名"),
            "default": Input("default", "默认值", var_type, "默认值", optional=True)
        }
        outputs = {
            "value": Output("value", "变量值", var_type, "变量值")
        }
        super().__init__("get_variable", inputs, outputs)
        self.container = container
        self.var_type = var_type

    def execute(self, name: str, default: Optional[T] = None) -> Dict[str, T]:
        executor = self.container.resolve(WorkflowExecutor)
        value = executor.get_variable(name, default)
        
        # 类型检查
        if value is not None and not isinstance(value, self.var_type):
            raise TypeError(f"Variable '{name}' must be of type {self.var_type}, got {type(value)}")
        
        return {"value": value} 