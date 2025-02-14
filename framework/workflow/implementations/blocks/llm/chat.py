from typing import Any, Dict, List, Optional
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.llm.llm_manager import LLMManager
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output
from framework.config.global_config import GlobalConfig
from framework.im.message import IMMessage, TextMessage
from datetime import datetime
class ChatMessageConstructor(Block):
    def __init__(self, container: DependencyContainer, system_prompt_format: str, user_prompt_format: str):
        inputs = {
            "user_msg": Input("user_msg", IMMessage, "Input message"),
            "memory_content": Input("memory_content", str, "Memory content")
        }
        outputs = {"llm_msg": Output("llm_msg", List[LLMChatMessage], "LLM message")}
        super().__init__("chat_message_constructor", inputs, outputs)
        self.container = container
        self.system_prompt_format = system_prompt_format
        self.user_prompt_format = user_prompt_format

    def execute(self, user_msg: IMMessage, memory_content: str) -> Dict[str, Any]:
        system_prompt = self.system_prompt_format.replace("{current_date_time}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        system_prompt = system_prompt.replace("{user_msg}", user_msg.content)
        system_prompt = system_prompt.replace("{memory_content}", memory_content)

        user_prompt = self.user_prompt_format.replace("{user_msg}", user_msg.content)
        user_prompt = user_prompt.replace("{memory_content}", memory_content)

        llm_msg = [
            LLMChatMessage(role='system', content=system_prompt),
            LLMChatMessage(role='user', content=user_prompt)
        ]
        return {"llm_msg": llm_msg}

class ChatCompletion(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"prompt": Input("prompt", List[LLMChatMessage], "LLM prompt")}
        outputs = {"resp": Output("resp", LLMChatResponse, "LLM response")}
        super().__init__("chat_completion", inputs, outputs)
        self.container = container

    def execute(self, prompt: List[LLMChatMessage]) -> Dict[str, Any]:
        llm_manager = self.container.resolve(LLMManager)
        config = self.container.resolve(GlobalConfig)

        default_model = config.defaults.llm_model
        llm = llm_manager.get_llm(default_model)
        req = LLMChatRequest(messages=prompt, model=default_model)
        return {"resp": llm.chat(req)}

class ChatResponseConverter(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"resp": Input("resp", LLMChatResponse, "LLM response")}
        outputs = {"msg": Output("msg", IMMessage, "Output message")}
        super().__init__("chat_response_converter", inputs, outputs)
        self.container = container

    def execute(self, resp: LLMChatResponse) -> Dict[str, Any]:
        content = ""
        if resp.choices and resp.choices[0].message:
            content = resp.choices[0].message.content

        msg = IMMessage(
            sender="<@llm>",
            message_elements=[TextMessage(content)]
        )
        return {"msg": msg}
