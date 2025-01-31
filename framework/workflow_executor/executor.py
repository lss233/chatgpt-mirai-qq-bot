from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from framework.logger import get_logger
from .workflow import Workflow
from .block import Block

class WorkflowExecutor:
    def __init__(self, workflow: Workflow):
        """
        初始化 WorkflowExecutor 实例。
        
        :param workflow: 要执行的工作流对象
        """
        self.logger = get_logger("WorkflowExecutor")
        self.workflow = workflow
        self.compiled_plan = self._compile_workflow()

    def _compile_workflow(self) -> Dict[Block, List[Block]]:
        """
        编译工作流，生成块之间的依赖关系图。
        
        :return: 依赖关系图，键为源块，值为目标块列表
        """
        dependencies = defaultdict(list)
        
        # 构建块之间的依赖关系
        for wire in self.workflow.wires:
            dependencies[wire.source_block].append(wire.target_block)
            self.logger.debug(f"Added dependency: {wire.source_block.name} -> {wire.target_block.name}")

        # 验证连线的数据类型是否匹配
        for wire in self.workflow.wires:
            source_output = wire.source_block.outputs[wire.source_output]
            target_input = wire.target_block.inputs[wire.target_input]
            if not target_input.data_type == source_output.data_type:
                raise TypeError(f"Type mismatch in wire: {wire.source_block.name}.{wire.source_output} "
                                f"({source_output.data_type}) -> {wire.target_block.name}.{wire.target_input} "
                                f"({target_input.data_type})")

        self.logger.info("Workflow compilation completed successfully.")
        return dependencies

    def run(self) -> Dict[str, Any]:
        """
        执行工作流，返回每个块的执行结果。
        
        :return: 包含每个块执行结果的字典，键为块名，值为块的输出
        """
        results = defaultdict(dict)
        futures = {}

        with ThreadPoolExecutor() as executor:
            # 提交没有输入依赖的块到线程池
            for block in self.workflow.blocks:
                if not block.inputs:
                    futures[executor.submit(block.execute)] = block
                    self.logger.debug(f"Submitted block '{block.name}' with no inputs.")

            # 处理已完成的块并提交依赖它的块
            while futures:
                completed_future = next(as_completed(futures))
                completed_block = futures.pop(completed_future)

                try:
                    block_outputs = completed_future.result()
                    self.logger.info(f"Block '{completed_block.name}' executed successfully.")
                except Exception as e:
                    self.logger.error(f"Block '{completed_block.name}' execution failed: {e}")
                    raise RuntimeError(f"Block {completed_block.name} execution failed: {e}")

                results[completed_block.name] = block_outputs

                # 检查依赖于当前块的块，并提交它们到线程池
                for dependent_block in self.compiled_plan.get(completed_block, []):
                    all_inputs_satisfied = True
                    block_inputs = {}

                    for input_name, input_obj in dependent_block.inputs.items():
                        for wire in self.workflow.wires:
                            if (wire.target_block == dependent_block and
                                wire.target_input == input_name and
                                wire.source_block.name in results):
                                block_inputs[input_name] = results[wire.source_block.name][wire.source_output]
                                break
                        else:
                            all_inputs_satisfied = False
                            break

                    if all_inputs_satisfied:
                        futures[executor.submit(dependent_block.execute, **block_inputs)] = dependent_block
                        self.logger.debug(f"Submitted dependent block '{dependent_block.name}' with inputs: {block_inputs}")

        self.logger.info("Workflow execution completed successfully.")
        return results