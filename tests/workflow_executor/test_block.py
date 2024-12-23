from framework.workflow_executor.block import Block
from framework.workflow_executor.input_output import Input, Output

# Define test inputs and outputs
input_data = Input(name="input1", data_type=str, description="Input data")
output_data = Output(name="output1", data_type=str, description="Processed data")

# Define test block
block = Block(name="TestBlock", inputs={"input1": input_data}, outputs={"output1": output_data})

def test_block_creation():
    """Test block creation."""
    assert block.name == "TestBlock"
    assert block.inputs["input1"].data_type == str
    assert block.outputs["output1"].data_type == str

def test_block_execute():
    """Test block execution."""
    result = block.execute(input1="test_input")
    assert "output1" in result
    assert result["output1"] == "Processed {'input1': 'test_input'}"