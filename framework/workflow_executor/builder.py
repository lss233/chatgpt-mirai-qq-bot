from typing import List, Type, Union, Callable, Dict, Any, Optional
from dataclasses import dataclass
from .block import Block
from .workflow import Workflow, Wire
from .control_blocks import ConditionBlock, LoopBlock, LoopEndBlock

@dataclass
class Node:
    block: Block
    name: Optional[str] = None  # 可选的 name 属性
    next_nodes: List['Node'] = None
    merge_point: 'Node' = None
    parallel_nodes: List['Node'] = None
    is_parallel: bool = False
    condition: Callable = None
    is_conditional: bool = False
    is_loop: bool = False  # 添加 is_loop 标记
    parent: 'Node' = None

    def __post_init__(self):
        self.next_nodes = self.next_nodes or []
        if not self.name:
            self.name = f"{self.block.__class__.__name__}_{id(self)}"

    def ancestors(self) -> List['Node']:
        """获取所有祖先节点"""
        result = []
        current = self.parent
        while current:
            result.append(current)
            current = current.parent
        return result

class WorkflowBuilder:
    """工作流构建器，提供流畅的 DSL 语法来构建工作流。

    基本语法:
    1. 初始化:
        builder = WorkflowBuilder("workflow_name", container)

    2. 添加节点的方法:
        .use(BlockClass)                    # 添加初始节点
        .chain(BlockClass)                  # 链式添加节点
        .parallel([BlockClass1, BlockClass2]) # 并行添加多个节点

    3. 节点配置格式:
        - BlockClass                                    # 最简单形式
        - (BlockClass, name)                           # 指定名称
        - (BlockClass, wire_from)                     # 指定连接来源
        - (BlockClass, kwargs)                         # 指定参数
        - (BlockClass, name, kwargs)                   # 指定名称和参数
        - (BlockClass, name, wire_from)                # 指定名称和连接来源
        - (BlockClass, name, kwargs, wire_from)        # 指定名称、参数和连接来源

    4. 控制流:
        .if_then(condition)                 # 条件分支开始
        .else_then()                        # else 分支
        .end_if()                          # 条件分支结束
        .loop(condition)                    # 循环开始
        .end_loop()                         # 循环结束

    完整示例:
    ```python
    workflow = (WorkflowBuilder("example", container)
        # 基本用法
        .use(InputBlock)                    # 最简单形式
        .chain(ProcessBlock, name="process") # 指定名称
        .chain(TransformBlock,              # 指定参数
               kwargs={"param": "value"})
        
        # 并行处理
        .parallel([
            ProcessA,                       # 简单形式
            (ProcessB, "proc_b"),           # 指定名称
            (ProcessC, {"param": "val"}),   # 指定参数
            (ProcessD, "proc_d",            # 完整形式
             {"param": "val"}, 
             ["process"])                   # 指定连接来源
        ])
        
        # 条件分支
        .if_then(lambda ctx: ctx["value"] > 0)
            .chain(PositiveBlock)
        .else_then()
            .chain(NegativeBlock)
        .end_if()
        
        # 循环处理
        .loop(lambda ctx: ctx["count"] < 5)
            .chain(LoopBlock)
        .end_loop()
        
        # 多输入连接
        .chain(MergeBlock,
               wire_from=["proc_b", "proc_d"])
        
        .build())
    ```

    特性说明:
    1. 自动连接: 默认情况下，节点会自动与前一个节点连接
    2. 命名节点: 通过指定 name 可以后续引用该节点
    3. 参数传递: 可以通过 kwargs 字典传递构造参数
    4. 自定义连接: 通过 wire_from 指定输入来源
    5. 并行处理: parallel 方法支持多个节点并行执行
    6. 条件和循环: 支持基本的控制流结构

    注意事项:
    1. wire_from 引用的节点名称必须已经存在
    2. 条件和循环语句必须正确配对
    3. 并行节点可以各自指定不同的连接来源
    4. 节点名称在工作流中必须唯一
    """

    def __init__(self, name: str, container):
        self.name = name
        self.container = container
        self.head: Node = None
        self.current: Node = None
        self.blocks: List[Block] = []
        self.wires: List[Wire] = []
        self.nodes_by_name: Dict[str, Node] = {}

    def use(self, block_class: Type[Block], name: str = None, **kwargs) -> 'WorkflowBuilder':
        block = block_class(self.container, **kwargs)
        node = Node(block=block, name=name)
        self.blocks.append(block)
        self.nodes_by_name[node.name] = node
        self.head = node
        self.current = node
        return self

    def chain(self, block_class: Type[Block], name: str = None, wire_from: List[str] = None, **kwargs) -> 'WorkflowBuilder':
        block = block_class(self.container, **kwargs)
        node = Node(block=block, name=name)
        self.blocks.append(block)
        self.nodes_by_name[node.name] = node
        
        if wire_from:
            for source_name in wire_from:
                source_node = self.nodes_by_name.get(source_name)
                if source_node:
                    self._connect_blocks(source_node.block, block)
        else:
            self._connect_blocks(self.current.block, block)
            
        self.current.next_nodes.append(node)
        node.parent = self.current
        self.current = node
        return self

    def parallel(self, block_specs: List[Union[Type[Block], tuple]]) -> 'WorkflowBuilder':
        """并行添加多个节点
        支持的 block_specs 格式:
        - BlockClass
        - (BlockClass, name)
        - (BlockClass, kwargs)
        - (BlockClass, wire_from)
        - (BlockClass, name, kwargs)
        - (BlockClass, kwargs, wire_from)
        - (BlockClass, name, kwargs, wire_from)
        """
        parallel_nodes = []
        # 初始化变量
        block_class, kwargs, name, wire_from = None, None, None, None

        for block_spec in block_specs:
            if isinstance(block_spec, tuple):
                if len(block_spec) == 4:  # (BlockClass, name, kwargs, wire_from)
                    block_class, name, kwargs, wire_from = block_spec
                elif len(block_spec) == 3:  # (BlockClass, name, kwargs) or (BlockClass, kwargs, wire_from)
                    block_class, second, third = block_spec
                    if isinstance(second, dict): # (BlockClass, kwargs, wire_from)
                        kwargs, name, wire_from = second, None, third
                    else: # (BlockClass, name, kwargs)
                        kwargs, name, wire_from = third, second, None
                elif len(block_spec) == 2:  # (BlockClass, kwargs) or (BlockClass, name) or (BlockClass, wire_from)
                    block_class, second = block_spec
                    if isinstance(second, dict): # (BlockClass, kwargs)
                        kwargs, name, wire_from = second, None, None
                    elif isinstance(second, str): # (BlockClass, wire_from)
                        kwargs, name, wire_from = {}, None, second
                    else: # (BlockClass, name)
                        kwargs, name, wire_from = {}, second, None
            else:
                block_class, kwargs, name, wire_from = block_spec, {}, None, None
            block = block_class(self.container, **kwargs)
            node = Node(block=block, name=name, is_parallel=True)
            self.blocks.append(block)
            self.nodes_by_name[node.name] = node
            
            # 处理连接
            if wire_from:
                if isinstance(wire_from, str):
                    wire_from = [wire_from]
                for source_name in wire_from:
                    source_node = self.nodes_by_name.get(source_name)
                    if source_node:
                        self._connect_blocks(source_node.block, block)
            # else:
            self._connect_blocks(self.current.block, block)
                
            node.parent = self.current
            parallel_nodes.append(node)
            
        self.current.next_nodes.extend(parallel_nodes)
        self.current = parallel_nodes[0]
        self.current.parallel_nodes = parallel_nodes
        return self

    def condition(self, condition_func: Callable) -> 'WorkflowBuilder':
        """添加条件判断"""
        self.current.condition = condition_func
        return self

    def if_then(self, condition: Callable[[Dict[str, Any]], bool], name: str = None) -> 'WorkflowBuilder':
        condition_block = ConditionBlock(condition, self.current.block.outputs.copy())
        node = Node(block=condition_block, name=name, is_conditional=True)
        self.blocks.append(condition_block)
        self.nodes_by_name[node.name] = node
        
        self._connect_blocks(self.current.block, condition_block)
        self.current.next_nodes.append(node)
        node.parent = self.current
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

    def loop(self, condition: Callable[[Dict[str, Any]], bool], name: str = None, iteration_var: str = "index") -> 'WorkflowBuilder':
        """开始一个循环"""
        loop_block = LoopBlock(condition, self.current.block.outputs.copy(), iteration_var)
        node = Node(block=loop_block, name=name, is_loop=True)
        self.blocks.append(loop_block)
        self.nodes_by_name[node.name] = node
        
        self._connect_blocks(self.current.block, loop_block)
        self.current.next_nodes.append(node)
        node.parent = self.current
        self.current = node
        return self

    def end_loop(self) -> 'WorkflowBuilder':
        """结束循环"""
        if not any(n.is_loop for n in self.current.ancestors()):
            raise ValueError("end_loop must close a loop block")
        
        loop_end = LoopEndBlock(self.current.block.outputs.copy())
        node = Node(block=loop_end)
        self.blocks.append(loop_end)
        self.nodes_by_name[node.name] = node
        
        self._connect_blocks(self.current.block, loop_end)
        loop_start = next(n for n in self.current.ancestors() if n.is_loop)
        self._connect_blocks(loop_end, loop_start.block)
        
        node.parent = self.current
        self.current = node
        return self

    def _connect_blocks(self, source_block: Block, target_block: Block):
        """连接两个块，自动处理输入输出匹配"""
        for output_name, output in source_block.outputs.items():
            for input_name, input in target_block.inputs.items():
                # 遵循先到先得的原则，如果这个 input 已经存在了 wire，则直接跳过
                if any(wire.target_block == target_block and wire.target_input == input_name for wire in self.wires):
                    continue
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
        # Add unique name for each unnamed block
        for block in self.blocks:
            if not block.name:
                block.name = f"{block.__class__.__name__}_{id(block)}"
        return Workflow(self.name, self.blocks, self.wires) 