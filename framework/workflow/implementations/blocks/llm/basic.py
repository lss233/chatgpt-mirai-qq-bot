
# LLM 响应转纯文本
from typing import Any, Dict

from framework.ioc.container import DependencyContainer
from framework.llm.format.response import LLMChatResponse
from framework.workflow.core.block.base import Block
from framework.workflow.core.block.input_output import Input, Output


class LLMResponseToText(Block):
    """LLM 响应转纯文本"""

    name = "llm_response_to_text"
    container: DependencyContainer
    inputs = {"response": Input("response", "LLM 响应", LLMChatResponse, "LLM 响应")}
    outputs = {"text": Output("text", "纯文本", str, "纯文本")}

    def execute(self, response: LLMChatResponse) -> Dict[str, Any]:
        content = ""
        if response.choices and response.choices[0].message:
            content = content +response.choices[0].message.content

        return {"text": content}

