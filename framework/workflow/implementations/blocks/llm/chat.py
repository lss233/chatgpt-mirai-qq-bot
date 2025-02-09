from typing import Any, Dict, List, Optional
import re
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.llm.llm_manager import LLMManager
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output
from framework.config.global_config import GlobalConfig
from framework.im.message import IMMessage, TextMessage
from framework.workflow.core.execution.executor import WorkflowExecutor

class ChatMessageConstructor(Block):
    name = "chat_message_constructor"
    inputs = {
        "user_msg": Input("user_msg", IMMessage, "Input message"),
        "memory_content": Input("memory_content", str, "Memory content")
    }
    outputs = {"llm_msg": Output("llm_msg", List[LLMChatMessage], "LLM message")}
    container: DependencyContainer

    def __init__(self, system_prompt_format: str, user_prompt_format: str):
        self.system_prompt_format = system_prompt_format
        self.user_prompt_format = user_prompt_format

    def substitute_variables(self, text: str, executor: WorkflowExecutor) -> str:
        """
        替换文本中的变量占位符，支持对象属性和字典键的访问
        
        :param text: 包含变量占位符的文本，格式为 {variable_name} 或 {variable_name.attribute}
        :param executor: 工作流执行器实例
        :return: 替换后的文本
        """
        def replace_var(match):
            var_path = match.group(1).split('.')
            var_name = var_path[0]
            
            # 获取基础变量
            value = executor.get_variable(var_name, match.group(0))
            
            # 如果有属性/键访问
            for attr in var_path[1:]:
                try:
                    # 尝试字典键访问
                    if isinstance(value, dict):
                        value = value.get(attr, match.group(0))
                    # 尝试对象属性访问
                    elif hasattr(value, attr):
                        value = getattr(value, attr)
                    else:
                        # 如果无法访问，返回原始占位符
                        return match.group(0)
                except Exception:
                    # 任何异常都返回原始占位符
                    return match.group(0)
            
            return str(value)
            
        return re.sub(r'\{([^}]+)\}', replace_var, text)

    def execute(self, user_msg: IMMessage, memory_content: str) -> Dict[str, Any]:
        # 获取当前执行器
        executor = self.container.resolve(WorkflowExecutor)
        
        # 先替换自有的两个变量
        system_prompt_format = self.system_prompt_format.replace("{user_msg}", user_msg.content)
        system_prompt_format = system_prompt_format.replace("{user_name}", user_msg.sender.display_name)
        system_prompt_format = system_prompt_format.replace("{memory_content}", memory_content)
        
        user_prompt_format = self.user_prompt_format.replace("{user_msg}", user_msg.content)
        user_prompt_format = user_prompt_format.replace("{user_name}", user_msg.sender.display_name)
        user_prompt_format = user_prompt_format.replace("{memory_content}", memory_content)
        
        # 再替换其他变量
        system_prompt = self.substitute_variables(system_prompt_format, executor)
        user_prompt = self.substitute_variables(user_prompt_format, executor)
        
        llm_msg = [
            LLMChatMessage(role='system', content=system_prompt),
            LLMChatMessage(role='user', content=user_prompt)
        ]
        return {"llm_msg": llm_msg}

class ChatCompletion(Block):
    name = "chat_completion"
    inputs = {"prompt": Input("prompt", List[LLMChatMessage], "LLM prompt")}
    outputs = {"resp": Output("resp", LLMChatResponse, "LLM response")}
    container: DependencyContainer

    def execute(self, prompt: List[LLMChatMessage]) -> Dict[str, Any]:
        llm_manager = self.container.resolve(LLMManager)
        config = self.container.resolve(GlobalConfig)
        
        default_model = config.defaults.llm_model
        llm = llm_manager.get_llm(default_model)
        req = LLMChatRequest(messages=prompt, model=default_model)
        return {"resp": llm.chat(req)}

class ChatResponseConverter(Block):
    name = "chat_response_converter"
    inputs = {"resp": Input("resp", LLMChatResponse, "LLM response")}
    outputs = {"msg": Output("msg", IMMessage, "Output message")}
    container: DependencyContainer

    def execute(self, resp: LLMChatResponse) -> Dict[str, Any]:
        content = ""
        if resp.choices and resp.choices[0].message:
            content = resp.choices[0].message.content
        
        # 通过 <break> 将回答分为不同的 TextMessage
        message_elements = []
        for element in content.split("<break>"):
            if element.strip():
                message_elements.append(TextMessage(element))
        msg = IMMessage(
            sender="<@llm>",
            message_elements=message_elements
        )
        return {"msg": msg} 