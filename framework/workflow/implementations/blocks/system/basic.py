from typing import Any, Dict
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Output

class TextBlock(Block):
    name = "text_block"
    outputs = {"text": Output("text", "文本", str, "文本")}

    def __init__(self, text: str):
        self.text = text

    def execute(self) -> Dict[str, Any]:
        return {"text": self.text}
