import pytest
from framework.workflow.core.block import Block
from framework.workflow.core.workflow import Wire, Workflow
from framework.workflow.core.workflow.input_output import Input, Output

# Define test blocks
input_block = Block(name="InputBlock", inputs={}, outputs={"output1": Output(name="output1", data_type=str, description="Input data")})
bad_block = Block(name="InputBlock", inputs={}, outputs={"output1": Output(name="output1", data_type=int, description="Input data")})
process_block = Block(name="ProcessBlock", inputs={"input1": Input(name="input1", data_type=str, description="Input data")},
                      outputs={"output1": Output(name="output1", data_type=str, description="Processed data")})

# Define test wires
wire = Wire(source_block=input_block, source_output="output1", target_block=process_block, target_input="input1")

def test_workflow_creation():
    """Test workflow creation."""
    workflow = Workflow(name="test_workflow", blocks=[input_block, process_block], wires=[wire])
    assert len(workflow.blocks) == 2
    assert len(workflow.wires) == 1
    assert workflow.wires[0].source_block == input_block
    assert workflow.wires[0].target_block == process_block