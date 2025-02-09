from typing import Callable, Any, Dict, Optional

from framework.workflow.core.block.input_output import Input, Output

class Block:
    """block 的基类"""
    # block 的 id
    id: str
    # block 的名称
    name: str
    # block 的输入
    inputs: Dict[str, Input] = {}
    # block 的输出
    outputs: Dict[str, Output] = {}
    

    def __init__(self, name: Optional[str] = None, inputs: Optional[Dict[str, Input]] = None, outputs: Optional[Dict[str, Output]] = None):
        self.id = getattr(self.__class__, "id", 'anonymous_' + self.__class__.__name__)
        if name is not None:
            self.name = name
        if inputs is not None:
            self.inputs = inputs
        if outputs is not None:
            self.outputs = outputs


    def execute(self, **kwargs) -> Dict[str, Any]:
        # Placeholder for block logic
        return {output: f"Processed {kwargs}" for output in self.outputs}
    
class ConditionBlock(Block):
    """条件判断块"""
    name: str = "condition"
    outputs: Dict[str, Output] = {"condition_result": Output("condition_result", bool, "Condition result")}
    
    def __init__(self, condition_func: Callable[[Dict[str, Any]], bool], inputs: Dict[str, 'Input']):
        super().__init__()
        self.inputs = inputs
        self.condition_func = condition_func

    def execute(self, **kwargs) -> Dict[str, Any]:
        result = self.condition_func(kwargs)
        return {"condition_result": result}

class LoopBlock(Block):
    """循环控制块"""
    name: str = "loop"
    outputs: Dict[str, Output] = {
        "should_continue": Output("should_continue", bool, "Continue loop?"),
        "iteration": Output("iteration", dict, "Current iteration data")
    }
    
    def __init__(self, 
                 condition_func: Callable[[Dict[str, Any]], bool],
                 inputs: Dict[str, 'Input'],
                 iteration_var: str = "index"):
        super().__init__()
        self.inputs = inputs
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
    name: str = "loop_end"
    outputs: Dict[str, Output] = {"loop_results": Output("loop_results", list, "Collected loop results")}
    
    def __init__(self, inputs: Dict[str, 'Input']):
        super().__init__()
        self.inputs = inputs
        self.results = []

    def execute(self, **kwargs) -> Dict[str, Any]:
        self.results.append(kwargs)
        return {"loop_results": self.results} 