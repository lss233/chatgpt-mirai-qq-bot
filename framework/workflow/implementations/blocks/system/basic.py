import re
from typing import Annotated, Any, Dict

from framework.workflow.core.block import Block, Output, ParamMeta
from framework.workflow.core.block.input_output import Input


class TextBlock(Block):
    name = "text_block"
    outputs = {"text": Output("text", "文本", str, "文本")}

    def __init__(
        self, text: Annotated[str, ParamMeta(label="文本", description="要输出的文本")]
    ):
        self.text = text

    def execute(self) -> Dict[str, Any]:
        return {"text": self.text}


# 拼接文本
class TextConcatBlock(Block):
    name = "text_concat_block"
    inputs = {
        "text1": Input("text1", "文本1", str, "文本1"),
        "text2": Input("text2", "文本2", str, "文本2"),
    }
    outputs = {"text": Output("text", "拼接后的文本", str, "拼接后的文本")}

    def execute(self) -> Dict[str, Any]:
        return {"text": self.text1.value + self.text2.value}


# 替换输入文本中的某一块文字为变量
class TextReplaceBlock(Block):
    name = "text_replace_block"
    inputs = {
        "text": Input("text", "原始文本", str, "原始文本"),
        "variable": Input("variable", "被替换的文本", Any, "被替换的文本"),
    }
    outputs = {"text": Output("text", "替换后的文本", str, "替换后的文本")}

    def __init__(
        self, name: Annotated[str, ParamMeta(label="变量名称", description="变量名称")]
    ):
        self.name = name

    def execute(self) -> Dict[str, Any]:
        return {
            "text": self.text.value.replace(self.variable.value, str(self.variable))
        }


# 正则表达式提取
class TextExtractByRegexBlock(Block):
    name = "text_extract_by_regex_block"
    inputs = {"text": Input("text", "原始文本", str, "原始文本")}
    outputs = {"text": Output("text", "提取后的文本", str, "提取后的文本")}

    def execute(self) -> Dict[str, Any]:
        # 使用正则表达式提取文本
        regex = re.compile(self.regex.value)
        match = regex.search(self.text.value)
        if match:
            return {"text": match.group(0)}
        else:
            return {"text": ""}
