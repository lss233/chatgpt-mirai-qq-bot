import os
import warnings
from typing import Any, Dict

import pytest

from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.core.block import Block
from kirara_ai.workflow.core.block.input_output import Input, Output
from kirara_ai.workflow.core.block.registry import BlockRegistry
from kirara_ai.workflow.core.workflow.builder import WorkflowBuilder


# 测试用的 Block 类
class SimpleInputBlock(Block):
    """简单的输入块"""

    name: str = "simple_input"
    inputs: Dict[str, Input] = {"param1": Input("param1", "输入1", str, "Input 1")}
    outputs: Dict[str, Output] = {"out1": Output("out1", "输出1", str, "Output 1")}

    def __init__(self, param1: str = "default"):
        super().__init__()
        self.param1 = param1

    def execute(self) -> Dict[str, Any]:
        return {"out1": self.param1}


class SimpleProcessBlock(Block):
    """简单的处理块"""

    name: str = "simple_process"
    inputs: Dict[str, Input] = {"in1": Input("in1", "输入1", str, "Input 1")}
    outputs: Dict[str, Output] = {"out1": Output("out1", "输出1", str, "Output 1")}

    def __init__(self, multiplier: int = 1):
        super().__init__()
        self.multiplier = multiplier

    def execute(self, in1: str) -> Dict[str, Any]:
        return {"out1": in1 * self.multiplier}


def setup_module(module):
    """测试模块开始前的设置"""
    registry = BlockRegistry()
    # 注册测试用的 block
    registry.register("simple_input", "test", SimpleInputBlock)
    registry.register("simple_process", "test", SimpleProcessBlock)


def teardown_module(module):
    """测试模块结束后的清理"""
    BlockRegistry().clear()


class TestWorkflowBuilder:
    @pytest.fixture
    def container(self):
        container = DependencyContainer()
        registry = BlockRegistry()
        container.register(BlockRegistry, registry)
        # 注册测试用的 block
        registry.register("simple_input", "test", SimpleInputBlock)
        registry.register("simple_process", "test", SimpleProcessBlock)
        return container

    @pytest.fixture
    def yaml_path(self):
        path = "test_workflow.yaml"
        yield path
        # 清理测试文件
        if os.path.exists(path):
            os.remove(path)

    def test_basic_dsl_construction(self, container):
        """测试基本的 DSL 构建功能"""
        builder = (
            WorkflowBuilder("test_workflow")
            .use(SimpleInputBlock, name="input1", param1="test")
            .chain(SimpleProcessBlock, name="process1", multiplier=2)
        )

        workflow = builder.build(container)

        assert len(workflow.blocks) == 2
        assert len(workflow.wires) == 1
        assert workflow.blocks[0].name == "input1"
        assert workflow.blocks[1].name == "process1"

    def test_parallel_construction(self, container):
        """测试并行节点构建"""
        builder = (
            WorkflowBuilder("test_workflow")
            .use(SimpleInputBlock)
            .parallel(
                [
                    (SimpleProcessBlock, "process1", {"multiplier": 2}),
                    (SimpleProcessBlock, "process2", {"multiplier": 3}),
                ]
            )
        )

        workflow = builder.build(container)

        assert len(workflow.blocks) == 3
        assert len(workflow.wires) == 2
        assert any(block.name == "process1" for block in workflow.blocks)
        assert any(block.name == "process2" for block in workflow.blocks)

    def test_save_and_load(self, container, yaml_path):
        """测试工作流的保存和加载"""
        # 构建原始工作流
        original_builder = (
            WorkflowBuilder("test_workflow")
            .use(SimpleInputBlock, name="input1", param1="test")
            .parallel(
                [
                    (SimpleProcessBlock, "process1", {"multiplier": 2}),
                    (SimpleProcessBlock, "process2", {"multiplier": 3}),
                ]
            )
        )

        # 保存工作流
        original_builder.save_to_yaml(yaml_path, container)

        # 加载工作流
        loaded_builder = WorkflowBuilder.load_from_yaml(yaml_path, container)
        loaded_workflow = loaded_builder.build(container)

        # 验证加载后的工作流

        assert len(loaded_workflow.blocks) == 3
        assert loaded_workflow.name == "test_workflow"

        # 验证参数是否正确加载
        input_block = next(b for b in loaded_workflow.blocks if b.name == "input1")
        assert input_block.param1 == "test"

        process1 = next(b for b in loaded_workflow.blocks if b.name == "process1")
        assert process1.multiplier == 2

        process2 = next(b for b in loaded_workflow.blocks if b.name == "process2")
        assert process2.multiplier == 3

    def test_complex_workflow_serialization(self, container, yaml_path):
        """测试复杂工作流的序列化"""
        # 构建一个包含多种特性的复杂工作流
        builder = (
            WorkflowBuilder("complex_workflow")
            .use(SimpleInputBlock, name="start", param1="init")
            .parallel(
                [
                    (SimpleProcessBlock, "parallel1", {"multiplier": 2}),
                    (SimpleProcessBlock, "parallel2", {"multiplier": 3}),
                ]
            )
            .chain(
                SimpleProcessBlock,
                name="final",
                wire_from=["parallel1", "parallel2"],
                multiplier=1,
            )
        )

        # 保存工作流
        builder.save_to_yaml(yaml_path, container)

        # 加载工作流
        loaded_builder = WorkflowBuilder.load_from_yaml(yaml_path, container)
        loaded_workflow = loaded_builder.build(container)

        # 验证结构
        assert len(loaded_workflow.blocks) == 4
        assert len(loaded_workflow.wires) >= 3  # 至少应该有3个连接

        # 验证特定节点的存在和配置
        assert any(b.name == "start" for b in loaded_workflow.blocks)
        assert any(b.name == "parallel1" for b in loaded_workflow.blocks)
        assert any(b.name == "parallel2" for b in loaded_workflow.blocks)
        assert any(b.name == "final" for b in loaded_workflow.blocks)

    def test_invalid_yaml_handling(self, container):
        """测试处理无效 YAML 文件的情况"""
        with pytest.raises(Exception):
            WorkflowBuilder.load_from_yaml("non_existent_file.yaml", container)

    def test_unregistered_block_warning(self, container, yaml_path):
        """测试未注册 block 的警告"""
        # 获取 registry 并清空
        registry = container.resolve(BlockRegistry)
        registry.clear()

        with pytest.warns(UserWarning):
            builder = WorkflowBuilder("test_workflow").use(SimpleInputBlock)
            builder.save_to_yaml(yaml_path, container)

    def test_registered_block_no_warning(self, container, yaml_path):
        """测试已注册 block 不会产生警告"""
        registry = container.resolve(BlockRegistry)
        registry.clear()
        registry.register("simple_input", "test", SimpleInputBlock)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            builder = WorkflowBuilder("test_workflow").use(SimpleInputBlock)
            builder.save_to_yaml(yaml_path, container)
