import pytest

from kirara_ai.events.event_bus import EventBus
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.core.block import Block, Input, Output
from kirara_ai.workflow.core.block.registry import BlockRegistry
from kirara_ai.workflow.core.execution.executor import WorkflowExecutor
from kirara_ai.workflow.core.workflow import Wire, Workflow
from tests.utils.test_block_registry import create_test_block_registry

# 创建测试用的 BlockRegistry
test_registry = create_test_block_registry()

# 创建测试用的 Block 类
class InputBlock(Block):
    name = "InputBlock"
    outputs = {
        "output1": Output(
            name="output1", label="输出1", data_type=str, description="Test output"
        )
    }

    def execute(self, **kwargs):
        return {"output1": "test_input"}


class ProcessBlock(Block):
    name = "ProcessBlock"
    inputs = {
        "input1": Input(
            name="input1", label="输入1", data_type=str, description="Test input"
        )
    }
    outputs = {
        "output1": Output(
            name="output1", label="输出1", data_type=str, description="Test output"
        )
    }

    def execute(self, input1: str, **kwargs):
        return {"output1": input1.upper()}


class OutputBlock(Block):
    name = "OutputBlock"
    inputs = {
        "input1": Input(
            name="input1", label="输入1", data_type=str, description="Test input"
        )
    }

    def execute(self, input1: str, **kwargs):
        return {"result": input1}


class FailingBlock(Block):
    name = "FailingBlock"
    inputs = {
        "input1": Input(
            name="input1", label="输入1", data_type=str, description="Test input"
        )
    }

    def execute(self, input1: str, **kwargs):
        raise RuntimeError("Test error")


# 注册测试用的 Block 类型
test_registry.register("test", "input", InputBlock)
test_registry.register("test", "process", ProcessBlock)
test_registry.register("test", "output", OutputBlock)
test_registry.register("test", "failing", FailingBlock)

# 创建测试用的工作流
input_block = InputBlock(name="input1")
process_block = ProcessBlock(name="process1")
output_block = OutputBlock(name="output1")

workflow = Workflow(
    name="test_workflow",
    blocks=[input_block, process_block, output_block],
    wires=[
        Wire(
            source_block=input_block,
            source_output="output1",
            target_block=process_block,
            target_input="input1",
        ),
        Wire(
            source_block=process_block,
            source_output="output1",
            target_block=output_block,
            target_input="input1",
        ),
    ],
)

# 创建测试用的失败工作流
failing_block = FailingBlock(name="failing1")
failing_workflow = Workflow(
    name="failing_workflow",
    blocks=[input_block, failing_block],
    wires=[
        Wire(
            source_block=input_block,
            source_output="output1",
            target_block=failing_block,
            target_input="input1",
        )
    ],
)


@pytest.mark.asyncio
async def test_executor_run():
    """Test workflow executor run."""
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    container.register(EventBus, EventBus())
    container.register(BlockRegistry, test_registry)
    container.register(Workflow, workflow)
    executor = WorkflowExecutor(container)
    result = await executor.run()

    assert result["input1"]["output1"] == "test_input"
    assert result["process1"]["output1"] == "TEST_INPUT"
    assert result["output1"]["result"] == "TEST_INPUT"


@pytest.mark.asyncio
async def test_executor_with_failing_block():
    """Test workflow executor with a failing block."""
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    container.register(EventBus, EventBus())
    container.register(BlockRegistry, test_registry)
    container.register(Workflow, failing_workflow)
    executor = WorkflowExecutor(container)
    with pytest.raises(RuntimeError, match="Block failing1 execution failed: Test error"):
        await executor.run()


@pytest.mark.asyncio
async def test_executor_with_no_blocks():
    """Test workflow executor with no blocks."""
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    container.register(EventBus, EventBus())
    container.register(BlockRegistry, test_registry)
    empty_workflow = Workflow(name="empty_workflow", blocks=[], wires=[])
    container.register(Workflow, empty_workflow)
    executor = WorkflowExecutor(container)
    result = await executor.run()
    assert result == {}


@pytest.mark.asyncio
async def test_executor_with_multiple_outputs():
    """Test workflow executor with a block that has multiple outputs."""
    # Define a block with multiple outputs
    multi_output_block = Block(
        name="MultiOutputBlock",
        inputs={
            "input1": Input(
                name="input1", label="输入1", data_type=str, description="Input data"
            )
        },
        outputs={
            "output1": Output(
                name="output1", label="输出1", data_type=str, description="First output"
            ),
            "output2": Output(
                name="output2",
                label="输出2",
                data_type=int,
                description="Second output",
            ),
        },
    )

    # Define a workflow with the multi-output block
    multi_output_workflow = Workflow(
        name="multi_output_workflow",
        blocks=[input_block, multi_output_block],
        wires=[
            Wire(
                source_block=input_block,
                source_output="output1",
                target_block=multi_output_block,
                target_input="input1",
            )
        ],
    )

    container = DependencyContainer()
    container.register(DependencyContainer, container)
    container.register(EventBus, EventBus())
    container.register(BlockRegistry, test_registry)
    container.register(Workflow, multi_output_workflow)
    executor = WorkflowExecutor(container)
    result = await executor.run()
    assert "MultiOutputBlock" in result
