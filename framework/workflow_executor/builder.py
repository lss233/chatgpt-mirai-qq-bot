from typing import List, Type, Union, Callable, Dict, Any
from dataclasses import dataclass
from .block import Block
from .workflow import Workflow, Wire
from .control_blocks import ConditionBlock, LoopBlock, LoopEndBlock

@dataclass
class Node:
    block: Block
    next_nodes: List['Node'] = None
    merge_point: 'Node' = None
    parallel_nodes: List['Node'] = None
    is_parallel: bool = False
    condition: Callable = None
    is_conditional: bool = False
    parent: 'Node' = None

    def __post_init__(self):
        self.next_nodes = self.next_nodes or []
    
class WorkflowBuilder:
    def __init__(self, name: str, container):
        self.name = name
        self.container = container
        self.head: Node = None
        self.current: Node = None
        self.blocks: List[Block] = []
        self.wires: List[Wire] = []

    def use(self, block_class: Type[Block], **kwargs) -> 'WorkflowBuilder':
        """添加一个初始节点"""
        block = block_class(self.container, **kwargs)
        node = Node(block=block)
        self.blocks.append(block)
        self.head = node
        self.current = node
        return self

    def chain(self, block_class: Type[Block], **kwargs) -> 'WorkflowBuilder':
        """链式添加一个节点"""
        block = block_class(self.container, **kwargs)
        node = Node(block=block)
        self.blocks.append(block)
        
        # 创建与前一个节点的连接
        self._connect_blocks(self.current.block, block)
        self.current.next_nodes.append(node)
        self.current = node
        return self

    def parallel(self, block_classes: List[Union[Type[Block], tuple]]) -> 'WorkflowBuilder':
        """并行添加多个节点"""
        parallel_nodes = []
        for block_spec in block_classes:
            if isinstance(block_spec, tuple):
                block_class, kwargs = block_spec
            else:
                block_class, kwargs = block_spec, {}
                
            block = block_class(self.container, **kwargs)
            node = Node(block=block, is_parallel=True)
            self.blocks.append(block)
            
            # 创建与前一个节点的连接
            self._connect_blocks(self.current.block, block)
            parallel_nodes.append(node)
            
        self.current.next_nodes.extend(parallel_nodes)
        self.current = parallel_nodes[0]
        self.current.merge_point = None  # 将在 merge 时设置
        self.current.parallel_nodes = parallel_nodes
        return self

    def merge(self, block_class: Type[Block], **kwargs) -> 'WorkflowBuilder':
        """合并并行节点"""
        merge_block = block_class(self.container, **kwargs)
        merge_node = Node(block=merge_block)
        self.blocks.append(merge_block)
        
        # 找到所有需要合并的并行节点
        parallel_nodes = self._find_parallel_nodes(self.current)
        for node in parallel_nodes:
            self._connect_blocks(node.block, merge_block)
            node.merge_point = merge_node
            
        self.current = merge_node
        return self

    def condition(self, condition_func: Callable) -> 'WorkflowBuilder':
        """添加条件判断"""
        self.current.condition = condition_func
        return self

    def if_then(self, condition: Callable[[Dict[str, Any]], bool]) -> 'WorkflowBuilder':
        """添加条件分支"""
        condition_block = ConditionBlock(condition, self.current.block.outputs.copy())
        node = Node(block=condition_block, is_conditional=True)
        self.blocks.append(condition_block)
        self._connect_blocks(self.current.block, condition_block)
        self.current.next_nodes.append(node)
        self.current = node
        return self

    def else_then(self) -> 'WorkflowBuilder':
        """添加else分支"""
        if not self.current.is_conditional:
            raise ValueError("else_then must follow if_then")
        self.current = self.current.parent
        return self

    def end_if(self) -> 'WorkflowBuilder':
        """结束条件分支"""
        if not self.current.is_conditional:
            raise ValueError("end_if must close an if block")
        self.current = self.current.merge_point or self.current
        return self

    def loop(self, condition: Callable[[Dict[str, Any]], bool], iteration_var: str = "index") -> 'WorkflowBuilder':
        """开始一个循环"""
        loop_block = LoopBlock(condition, self.current.block.outputs.copy(), iteration_var)
        node = Node(block=loop_block, is_loop=True)
        self.blocks.append(loop_block)
        self._connect_blocks(self.current.block, loop_block)
        self.current.next_nodes.append(node)
        self.current = node
        return self

    def end_loop(self) -> 'WorkflowBuilder':
        """结束循环"""
        if not any(n.is_loop for n in self.current.ancestors()):
            raise ValueError("end_loop must close a loop block")
        
        loop_end = LoopEndBlock(self.current.block.outputs.copy())
        node = Node(block=loop_end)
        self.blocks.append(loop_end)
        self._connect_blocks(self.current.block, loop_end)
        
        # 连接回循环开始
        loop_start = next(n for n in self.current.ancestors() if n.is_loop)
        self._connect_blocks(loop_end, loop_start.block)
        
        self.current = node
        return self

    def _connect_blocks(self, source_block: Block, target_block: Block):
        """连接两个块，自动处理输入输出匹配"""
        for output_name, output in source_block.outputs.items():
            for input_name, input in target_block.inputs.items():
                if output.data_type == input.data_type:
                    wire = Wire(source_block, output_name, target_block, input_name)
                    self.wires.append(wire)
                    break

    def _find_parallel_nodes(self, start_node: Node) -> List[Node]:
        """查找所有并行节点"""
        parallel_nodes = []
        current = start_node
        while current:
            if current.is_parallel:
                parallel_nodes.extend(current.parallel_nodes)
            if current.next_nodes:
                current = current.next_nodes[0]
            else:
                break
        return parallel_nodes

    def build(self) -> Workflow:
        """构建工作流"""
        return Workflow(self.name, self.blocks, self.wires) 