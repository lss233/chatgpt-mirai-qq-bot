from typing import Callable, Any, Dict

from framework.workflow.core.workflow.input_output import Input, Output

class Block:
    def __init__(self, name: str, inputs: Dict[str, Input], outputs: Dict[str, Output]):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs

    def execute(self, **kwargs) -> Dict[str, Any]:
        # Placeholder for block logic
        return {output: f"Processed {kwargs}" for output in self.outputs}
    
class ConditionBlock(Block):
    """条件判断块"""
    def __init__(self, condition_func: Callable[[Dict[str, Any]], bool], inputs: Dict[str, 'Input']):
        super().__init__(
            name="condition",
            inputs=inputs,
            outputs={"condition_result": Output("condition_result", bool, "Condition result")}
        )
        self.condition_func = condition_func

    def execute(self, **kwargs) -> Dict[str, Any]:
        result = self.condition_func(kwargs)
        return {"condition_result": result}

class LoopBlock(Block):
    """循环控制块"""
    def __init__(self, 
                 condition_func: Callable[[Dict[str, Any]], bool],
                 inputs: Dict[str, 'Input'],
                 iteration_var: str = "index"):
        super().__init__(
            name="loop",
            inputs=inputs,
            outputs={
                "should_continue": Output("should_continue", bool, "Continue loop?"),
                "iteration": Output("iteration", dict, "Current iteration data")
            }
        )
        self.condition_func = condition_func
        self.iteration_var = iteration_var
        self.iteration_count = 0

    def execute(self, **kwargs) -> Dict[str, Any]:
        should_continue = self.condition_func(kwargs)
        self.iteration_count += 1
        return {
            "should_continue": should_continue,
            "iteration": {
                self.iteration_var: self.iteration_count,
                **kwargs
            }
        }

class LoopEndBlock(Block):
    """循环结束块，收集循环结果"""
    def __init__(self, inputs: Dict[str, 'Input']):
        super().__init__(
            name="loop_end",
            inputs=inputs,
            outputs={"loop_results": Output("loop_results", list, "Collected loop results")}
        )
        self.results = []

    def execute(self, **kwargs) -> Dict[str, Any]:
        self.results.append(kwargs)
        return {"loop_results": self.results} 