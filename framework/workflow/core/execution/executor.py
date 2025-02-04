import asyncio
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools
from typing import Dict, Any, List

from framework.logger import get_logger
from framework.workflow.core.block import Block, ConditionBlock, LoopBlock
from framework.workflow.core.workflow import Workflow


class WorkflowExecutor:
    def __init__(self, workflow: Workflow):
        """
        初始化 WorkflowExecutor 实例。
        
        :param workflow: 要执行的工作流对象
        """
        self.logger = get_logger("WorkflowExecutor")
        self.workflow = workflow
        self.results = defaultdict(dict)
        self.variables = {}  # 存储工作流变量
        self.logger.info(f"Initializing WorkflowExecutor for workflow '{workflow.name}'")
        # self.logger.debug(f"Workflow has {len(workflow.blocks)} blocks and {len(workflow.wires)} wires")
        self._build_execution_graph()

    def _build_execution_graph(self):
        """构建执行图，包含并行和条件逻辑"""
        self.execution_graph = defaultdict(list)
        # self.logger.debug("Building execution graph...")
        
        for wire in self.workflow.wires:
            # self.logger.debug(f"Processing wire: {wire.source_block.name}.{wire.source_output} -> "
            #                  f"{wire.target_block.name}.{wire.target_input}")
            
            # 验证连线的数据类型是否匹配
            source_output = wire.source_block.outputs[wire.source_output]
            target_input = wire.target_block.inputs[wire.target_input]
            if not target_input.data_type == source_output.data_type:
                error_msg = (f"Type mismatch in wire: {wire.source_block.name}.{wire.source_output} "
                            f"({source_output.data_type}) -> {wire.target_block.name}.{wire.target_input} "
                            f"({target_input.data_type})")
                self.logger.error(error_msg)
                raise TypeError(error_msg)
            # 将目标块添加到源块的执行图中
            self.execution_graph[wire.source_block].append(wire.target_block)
            # self.logger.debug(f"Added edge: {wire.source_block.name} -> {wire.target_block.name}")

    async def run(self) -> Dict[str, Any]:
        """
        执行工作流，返回每个块的执行结果。

        :return: 包含每个块执行结果的字典，键为块名，值为块的输出
        """
        self.logger.info("Starting workflow execution")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # 从入口节点开始执行
            entry_blocks = [block for block in self.workflow.blocks if not block.inputs]
            # self.logger.debug(f"Identified entry blocks: {[b.name for b in entry_blocks]}")
            await self._execute_nodes(entry_blocks, executor, loop)
        
        self.logger.info("Workflow execution completed")
        return self.results

    async def _execute_nodes(self, blocks: List[Block], executor, loop):
        """执行一组节点"""
        # self.logger.debug(f"Executing node group: {[b.name for b in blocks]}")
        
        for block in blocks:
            # self.logger.debug(f"Processing block: {block.name} ({type(block).__name__})")
            if isinstance(block, ConditionBlock):
                await self._execute_conditional_branch(block, executor, loop)
            elif isinstance(block, LoopBlock):
                await self._execute_loop(block, executor, loop)
            else:
                await self._execute_normal_block(block, executor, loop)

    async def _execute_conditional_branch(self, block: ConditionBlock, executor, loop):
        """执行条件分支"""
        self.logger.info(f"Executing ConditionBlock: {block.name}")
        inputs = self._gather_inputs(block)
        # self.logger.debug(f"ConditionBlock inputs: {list(inputs.keys())}")
        
        result = await loop.run_in_executor(executor, block.execute, **inputs)
        self.results[block.name] = result
        self.logger.info(f"ConditionBlock {block.name} evaluation result: {result['condition_result']}")

        next_blocks = self.execution_graph[block]
        if result["condition_result"]:
            # self.logger.debug(f"Taking THEN branch: {next_blocks[0].name}")
            await self._execute_nodes([next_blocks[0]], executor, loop)
        elif len(next_blocks) > 1:
            # self.logger.debug(f"Taking ELSE branch: {next_blocks[1].name}")
            await self._execute_nodes([next_blocks[1]], executor, loop)
        else:
            # self.logger.debug("No ELSE branch available")
            pass

    async def _execute_loop(self, block: LoopBlock, executor, loop):
        """执行循环"""
        self.logger.info(f"Starting LoopBlock: {block.name}")
        iteration = 0
        
        while True:
            iteration += 1
            # self.logger.debug(f"LoopBlock {block.name} iteration #{iteration}")
            inputs = self._gather_inputs(block)
            # self.logger.debug(f"LoopBlock inputs: {list(inputs.keys())}")
            
            result = await loop.run_in_executor(executor, block.execute, **inputs)
            self.results[block.name] = result
            self.logger.info(f"LoopBlock {block.name} continuation check: {result['should_continue']}")

            if not result["should_continue"]:
                self.logger.info(f"Exiting LoopBlock {block.name} after {iteration} iterations")
                break

            # self.logger.debug(f"Executing loop body: {self.execution_graph[block][0].name}")
            loop_body = self.execution_graph[block][0]
            await self._execute_nodes([loop_body], executor, loop)

    async def _execute_normal_block(self, block: Block, executor, loop):
        """执行普通块"""
        # self.logger.debug(f"Evaluating Block: {block.name}")
        futures = []
        
        if self._can_execute(block):
            inputs = self._gather_inputs(block)
            self.logger.info(f"Executing Block: {block.name}")
            # self.logger.debug(f"Input parameters: {list(inputs.keys())}")
            
            future = loop.run_in_executor(
                executor,
                functools.partial(block.execute, **inputs)
            )
            futures.append((future, block))
        else:
            # self.logger.debug(f"Block {block.name} dependencies not met, skipping execution")
            return

        # 等待所有并行任务完成
        for future, block in futures:
            try:
                result = await future
                self.results[block.name] = result
                self.logger.info(f"Block {block.name} executed successfully")
                if result:
                    # self.logger.debug(f"Execution result keys: {list(result.keys())}")
                    pass
                next_blocks = self.execution_graph[block]
                if next_blocks:
                    # self.logger.debug(f"Propagating to next blocks: {[b.name for b in next_blocks]}")
                    await self._execute_nodes(next_blocks, executor, loop)
                else:
                    # self.logger.debug(f"Block {block.name} is terminal node")
                    pass
            except Exception as e:
                self.logger.error(f"Block {block.name} execution failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Block {block.name} execution failed: {e}")

    def _can_execute(self, block: Block) -> bool:
        """检查节点是否可以执行"""
        # self.logger.debug(f"Checking execution readiness for Block: {block.name}")

        # 如果块已经执行过，直接返回False
        if block.name in self.results:
            # self.logger.debug(f"Block {block.name} has already been executed")
            return False
    
        if not block.inputs:
            # self.logger.debug("No inputs required, ready to execute")
            return True
            
        for input_name in block.inputs:
            input_satisfied = False
            for wire in self.workflow.wires:
                if (wire.target_block == block and 
                    wire.target_input == input_name and
                    wire.source_block.name in self.results):
                    # self.logger.debug(f"Input {input_name} satisfied by {wire.source_block.name}")
                    input_satisfied = True
                    break
            
            if not input_satisfied:
                # self.logger.debug(f"Input {input_name} not satisfied")
                return False
        
        # self.logger.debug("All inputs satisfied")
        return True

    def _gather_inputs(self, block: Block) -> Dict[str, Any]:
        """收集节点的输入数据"""
        # self.logger.debug(f"Gathering inputs for Block: {block.name}")
        inputs = {}
        
        for input_name in block.inputs:
            for wire in self.workflow.wires:
                if (wire.target_block == block and 
                    wire.target_input == input_name and
                    wire.source_block.name in self.results):
                    inputs[input_name] = self.results[wire.source_block.name][wire.source_output]
                    # self.logger.debug(f"Resolved input {input_name} from {wire.source_block.name}")
                    break
        
        # self.logger.debug(f"Collected {len(inputs)} inputs")
        return inputs

    def set_variable(self, name: str, value: Any) -> None:
        """
        设置工作流变量
        
        :param name: 变量名
        :param value: 变量值
        """
        self.variables[name] = value
        
    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        获取工作流变量
        
        :param name: 变量名
        :param default: 默认值，如果变量不存在则返回此值
        :return: 变量值
        """
        return self.variables.get(name, default)