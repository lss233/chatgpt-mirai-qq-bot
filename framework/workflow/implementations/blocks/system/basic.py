from typing import Annotated, Any, Dict
from framework.workflow.core.block import Block, Output, ParamMeta

class TextBlock(Block):
    name = "text_block"
    outputs = {"text": Output("text", "文本", str, "文本")}

    def __init__(self, text: Annotated[str, ParamMeta(label="文本", description="要输出的文本")]):
        self.text = text

    def execute(self) -> Dict[str, Any]:
        return {"text": self.text}
