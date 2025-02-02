import asyncio
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools
from typing import Dict, Any, List

from framework.logger import get_logger
from .workflow import Workflow
from .block import Block
from .control_blocks import ConditionBlock, LoopBlock

class WorkflowExecutor:
    def __init__(self, workflow: Workflow):
        """
        初始化 WorkflowExecutor 实例。
        
        :param workflow: 要执行的工作流对象
        """
        self.logger = get_logger("WorkflowExecutor")
        self.workflow = workflow
        self.results = defaultdict(dict)
        self._build_execution_graph()

    def _build_execution_graph(self):
        """构建执行图，包含并行和条件逻辑"""
        self.execution_graph = defaultdict(list)
        # 验证连线的数据类型是否匹配
        for wire in self.workflow.wires:
            source_output = wire.source_block.outputs[wire.source_output]
            target_input = wire.target_block.inputs[wire.target_input]
            if not target_input.data_type == source_output.data_type:
                raise TypeError(f"Type mismatch in wire: {wire.source_block.name}.{wire.source_output} "
                                f"({source_output.data_type}) -> {wire.target_block.name}.{wire.target_input} "
                                f"({target_input.data_type})")
            
        for wire in self.workflow.wires:
            # 检验 wire 输入和输出的数据类型是否正确
            self.execution_graph[wire.source_block].append(wire.target_block)

    async def run(self) -> Dict[str, Any]:
        """
        执行工作流，返回每个块的执行结果。

        :return: 包含每个块执行结果的字典，键为块名，值为块的输出
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # 从入口节点开始执行
            entry_blocks = [block for block in self.workflow.blocks if not block.inputs]
            self.logger.info(f"Starting execution with {len(entry_blocks)} entry blocks")
            await self._execute_nodes(entry_blocks, executor, loop)
        return self.results

    async def _execute_nodes(self, blocks: List[Block], executor, loop):
        """执行一组节点"""
        for block in blocks:
            if isinstance(block, ConditionBlock):
                self.logger.info(f"Executing conditional block: {block.name}")
                await self._execute_conditional_branch(block, executor, loop)
            elif isinstance(block, LoopBlock):
                self.logger.info(f"Executing loop block: {block.name}")
                await self._execute_loop(block, executor, loop)
            else:
                self.logger.info(f"Executing normal block: {block.name}")
                await self._execute_normal_block(block, executor, loop)

    async def _execute_conditional_branch(self, block: ConditionBlock, executor, loop):
        """执行条件分支"""
        inputs = self._gather_inputs(block)
        result = await loop.run_in_executor(executor, block.execute, **inputs)
        self.results[block.name] = result

        next_blocks = self.execution_graph[block]
        if result["condition_result"]:
            # 执行 then 分支
            await self._execute_nodes([next_blocks[0]], executor, loop)
        elif len(next_blocks) > 1:
            # 执行 else 分支
            await self._execute_nodes([next_blocks[1]], executor, loop)

    async def _execute_loop(self, block: LoopBlock, executor, loop):
        """执行循环"""
        while True:
            inputs = self._gather_inputs(block)
            result = await loop.run_in_executor(executor, block.execute, **inputs)
            self.results[block.name] = result

            if not result["should_continue"]:
                break

            # 执行循环体
            loop_body = self.execution_graph[block][0]
            await self._execute_nodes([loop_body], executor, loop)

    async def _execute_normal_block(self, block: Block, executor, loop):
        """执行普通块"""
        futures = []
        if self._can_execute(block):
            inputs = self._gather_inputs(block)
            future = loop.run_in_executor(
                executor,
                functools.partial(block.execute, **inputs)
            )
            futures.append((future, block))

        # 等待所有并行任务完成
        for future, block in futures:
            try:
                result = await future
                self.results[block.name] = result
                self.logger.info(f"Result for block {block.name}: {result}")
                # 获取下一组要执行的节点
                next_blocks = self.execution_graph[block]
                self.logger.info(f"Next blocks for block {block.name}: {next_blocks}")
                if next_blocks:
                    await self._execute_nodes(next_blocks, executor, loop)
            except Exception as e:
                raise RuntimeError(f"Block {block.name} execution failed: {e}")

    def _can_execute(self, block: Block) -> bool:
        """检查节点是否可以执行"""
        self.logger.info(f"Checking if block {block.name} can execute")
        if not block.inputs:
            return True
            
        for input_name in block.inputs:
            input_satisfied = False
            for wire in self.workflow.wires:
                if (wire.target_block == block and 
                    wire.target_input == input_name and
                    wire.source_block.name in self.results):
                    input_satisfied = True
                    break
            if not input_satisfied:
                return False
        return True

    def _gather_inputs(self, block: Block) -> Dict[str, Any]:
        """收集节点的输入数据"""
        self.logger.info(f"Gathering inputs for block {block.name}")
        inputs = {}
        for input_name in block.inputs:
            for wire in self.workflow.wires:
                if (wire.target_block == block and 
                    wire.target_input == input_name and
                    wire.source_block.name in self.results):
                    inputs[input_name] = self.results[wire.source_block.name][wire.source_output]
                    break
        self.logger.info(f"Inputs for block {block.name}: {inputs}")
        return inputs