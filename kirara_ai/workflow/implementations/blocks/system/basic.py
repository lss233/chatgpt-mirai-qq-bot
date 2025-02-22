import re
from typing import Annotated, Any, Dict

from kirara_ai.workflow.core.block import Block, Output, ParamMeta
from kirara_ai.workflow.core.block.input_output import Input


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
        return {"text": self.text1 + self.text2}


# 替换输入文本中的某一块文字为变量
class TextReplaceBlock(Block):
    name = "text_replace_block"
    inputs = {
        "text": Input("text", "原始文本", str, "原始文本"),
        "new_text": Input("new_text", "新文本", Any, "新文本"),
    }
    outputs = {"text": Output("text", "替换后的文本", str, "替换后的文本")}

    def __init__(
        self, variable: Annotated[str, ParamMeta(label="被替换的文本", description="被替换的文本")]
    ):
        self.variable = variable

    def execute(self, text: str, new_text: Any) -> Dict[str, Any]:
        return {
            "text": text.replace(self.variable, str(new_text))
        }


# 正则表达式提取
class TextExtractByRegexBlock(Block):
    name = "text_extract_by_regex_block"
    inputs = {"text": Input("text", "原始文本", str, "原始文本")}
    outputs = {"text": Output("text", "提取后的文本", str, "提取后的文本")}
    def __init__(
        self, regex: Annotated[str, ParamMeta(label="正则表达式", description="正则表达式")]
    ):
        self.regex = regex

    def execute(self, text: str) -> Dict[str, Any]:
        # 使用正则表达式提取文本
        regex = re.compile(self.regex)
        match = regex.search(text)
        # 如果匹配到，则返回匹配到的文本，否则返回空字符串
        if match and len(match.groups()) > 0:
            return {"text": match.group(1)}
        else:
            return {"text": ""}
        