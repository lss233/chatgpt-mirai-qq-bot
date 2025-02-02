import pytest
from framework.workflow_executor.workflow import Workflow, Wire
from framework.workflow_executor.block import Block
from framework.workflow_executor.input_output import Input, Output
from framework.workflow_executor.executor import WorkflowExecutor

# Define test blocks
input_block = Block(name="InputBlock", inputs={}, outputs={"output1": Output(
    name="output1", data_type=str, description="Input data")})
process_block1 = Block(name="ProcessBlock1", inputs={"input1": Input(name="input1", data_type=str, description="Input data")},
                       outputs={"output1": Output(name="output1", data_type=str, description="Processed data")})
process_block2 = Block(name="ProcessBlock2", inputs={"input1": Input(name="input1", data_type=str, description="Input data")},
                       outputs={"output1": Output(name="output1", data_type=str, description="Processed data")})

# Define test wires
wire1 = Wire(source_block=input_block, source_output="output1",
             target_block=process_block1, target_input="input1")
wire2 = Wire(source_block=process_block1, source_output="output1",
             target_block=process_block2, target_input="input1")

# Define test workflow
workflow = Workflow(
    name="test_workflow",
    blocks=[input_block, process_block1, process_block2], wires=[wire1, wire2])

# Define a block with a failing execution


class FailingBlock(Block):
    def execute(self, **kwargs):
        raise RuntimeError("This block is supposed to fail.")


failing_block = FailingBlock(name="FailingBlock", inputs={"input1": Input(name="input1", data_type=str, description="Input data")}, outputs={
                             "output1": Output(name="output1", data_type=str, description="Failing output")})

# Define a workflow with a failing block
failing_workflow = Workflow(name="failing_workflow", blocks=[input_block, failing_block], wires=[Wire(
    source_block=input_block, source_output="output1", target_block=failing_block, target_input="input1")])


@pytest.mark.asyncio
async def test_executor_run():
    """Test workflow executor run."""
    executor = WorkflowExecutor(workflow)
    results = await executor.run()

    # Check results
    assert "InputBlock" in results
    assert "ProcessBlock1" in results
    assert "ProcessBlock2" in results

    assert results["InputBlock"]["output1"] == "Processed {}"
    assert results["ProcessBlock1"]["output1"] == "Processed {'input1': 'Processed {}'}"
    assert results["ProcessBlock2"][
        "output1"] == "Processed {'input1': \"Processed {'input1': 'Processed {}'}\"}"


def test_executor_type_mismatch():
    """Test type mismatch in executor."""
    # Create a wire with mismatched types
    wrong_process_block = Block(name="ProcessBlock1", inputs={"input1": Input(name="input1", data_type=int, description="Input data")},
                       outputs={"output1": Output(name="output1", data_type=str, description="Processed data")})
    
    mismatched_wire = Wire(
        source_block=input_block,
        source_output="output1",
        target_block=wrong_process_block,
        target_input="input1"
    )
    # Create a workflow with mismatched wire
    mismatched_workflow = Workflow(
        name="mismatched_workflow",
        blocks=[input_block, wrong_process_block], wires=[mismatched_wire])

    with pytest.raises(TypeError):
        WorkflowExecutor(mismatched_workflow)


@pytest.mark.asyncio
async def test_executor_with_failing_block():
    """Test workflow executor with a failing block."""
    executor = WorkflowExecutor(failing_workflow)
    with pytest.raises(RuntimeError) as exc_info:
        await executor.run()

@pytest.mark.asyncio
async def test_executor_with_no_blocks():
    """Test workflow executor with no blocks."""
    empty_workflow = Workflow(name="empty_workflow", blocks=[], wires=[])
    executor = WorkflowExecutor(empty_workflow)
    results = await executor.run()

    # Check that the results are empty
    assert results == {}

@pytest.mark.asyncio
async def test_executor_with_multiple_outputs():
    """Test workflow executor with a block that has multiple outputs."""
    # Define a block with multiple outputs
    multi_output_block = Block(
        name="MultiOutputBlock",
        inputs={"input1": Input(
            name="input1", data_type=str, description="Input data")},
        outputs={
            "output1": Output(name="output1", data_type=str, description="First output"),
            "output2": Output(name="output2", data_type=int, description="Second output"),
        }
    )

    # Define a workflow with the multi-output block
    multi_output_workflow = Workflow(
        name="multi_output_workflow",
        blocks=[input_block, multi_output_block],
        wires=[Wire(source_block=input_block, source_output="output1",
                    target_block=multi_output_block, target_input="input1")]
    )

    executor = WorkflowExecutor(multi_output_workflow)
    results = await executor.run()

    # Check results
    assert "InputBlock" in results
    assert "MultiOutputBlock" in results
    assert results["InputBlock"]["output1"] == "Processed {}"
    assert results["MultiOutputBlock"]["output1"] == "Processed {'input1': 'Processed {}'}"
    assert results["MultiOutputBlock"]["output2"] == "Processed {'input1': 'Processed {}'}"
