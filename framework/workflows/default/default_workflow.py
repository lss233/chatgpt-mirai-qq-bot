from typing import Any, Dict, List
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.llm.llm_manager import LLMManager
from framework.workflow_executor.builder import WorkflowBuilder
from framework.workflow_executor.workflow import Workflow
from framework.im.message import IMMessage, TextMessage
from framework.ioc.container import DependencyContainer
from framework.workflow_executor.block import Block
from framework.workflow_executor.input_output import Input, Output
from framework.config.global_config import GlobalConfig
from framework.workflows.blocks.im.messages import GetIMMessage, SendIMMessage
from framework.workflows.blocks.im.states import ToggleEditState
from framework.memory.memory_adapter import MemoryAdapter


class QueryChatMemory(Block):
    def __init__(self, container: DependencyContainer, memory_adapter: str):
        inputs = {"msg": Input("msg", IMMessage, "Input message")}
        outputs = {"memory_content": Output("memory_content", str, "memory messages")}
        super().__init__("query_chat_memory", inputs, outputs)
        self.container = container
        self.memory_adapter = MemoryAdapter(container)

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        # 从消息中获取发送者和内容
        sender = msg.sender
        content = msg.content
        
        # 使用 memory adapter 查询历史记忆
        memory_content = self.memory_adapter.query(sender=sender, content=content)
        return {"memory_content": memory_content}
    
class ConstructLLMMessage(Block):
    def __init__(self, container: DependencyContainer, system_prompt_format: str, user_prompt_format: str):
        inputs = {
            "user_msg": Input("user_msg", IMMessage, "Input message"),
            "memory_content": Input("memory_content", str, "Memory content")
        }
        outputs = {"llm_msg": Output("llm_msg", List[LLMChatMessage], "LLM message")}
        super().__init__("construct_llm_message", inputs, outputs)
        self.container = container
        self.system_prompt_format = system_prompt_format
        self.user_prompt_format = user_prompt_format

    def execute(self, user_msg: IMMessage, memory_content: str) -> Dict[str, Any]:
        # 替换提示模板中的变量
        system_prompt = self.system_prompt_format.replace("{user_msg}", user_msg.content)
        system_prompt = system_prompt.replace("{memory_content}", memory_content)
        
        user_prompt = self.user_prompt_format.replace("{user_msg}", user_msg.content)
        user_prompt = user_prompt.replace("{memory_content}", memory_content)
        
        llm_msg = [
            LLMChatMessage(role='system', content=system_prompt),
            LLMChatMessage(role='user', content=user_prompt)
        ]
        return {"llm_msg": llm_msg}

class LLMChat(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"prompt": Input("prompt", List[LLMChatMessage], "LLM prompt")}
        outputs = {"resp": Output("resp", LLMChatResponse, "LLM response")}
        super().__init__("llm_chat", inputs, outputs)
        self.container = container

    def execute(self, prompt: List[LLMChatMessage]) -> Dict[str, Any]:
        llm_manager = self.container.resolve(LLMManager)
        config = self.container.resolve(GlobalConfig)
        
        default_model = config.defaults.llm_model
        llm = llm_manager.get_llm(default_model)
        req = LLMChatRequest(messages=prompt, model=default_model)
        return {"resp": llm.chat(req)}

class LLMToMessage(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"resp": Input("resp", LLMChatResponse, "LLM response")}
        outputs = {"msg": Output("msg", IMMessage, "Output message")}
        super().__init__("llm_to_msg", inputs, outputs)
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

class StoreMemory(Block):
    def __init__(self, container: DependencyContainer, memory_adapter: str):
        inputs = {
            "user_msg": Input("user_msg", IMMessage, "User message"),
            "llm_resp": Input("llm_resp", LLMChatResponse, "LLM response message")
        }
        outputs = {}  # 不需要输出
        super().__init__("store_memory", inputs, outputs)
        self.container = container
        self.memory_adapter = MemoryAdapter(container)

    def execute(self, user_msg: IMMessage, llm_resp: LLMChatResponse) -> Dict[str, Any]:
        # 存储用户消息
        self.memory_adapter.store(
            sender=user_msg.sender,
            content=user_msg.content
        )
        
        # 存储 LLM 响应
        self.memory_adapter.store(
            sender=llm_resp.choices[0].message.role,
            content=llm_resp.choices[0].message.content
        )
        
        return {}

def create_default_workflow(container: DependencyContainer) -> Workflow:
    """使用 DSL 创建默认工作流"""    
    system_prompt = """你是一个智能助手。以下是之前的对话历史：
{memory_content}

请基于以上历史记忆，回答用户的问题。"""

    user_prompt = """{user_msg}"""
    
    return (WorkflowBuilder("default_workflow", container)
        .use(GetIMMessage, name="get_message")
        .parallel([
            (ToggleEditState, {"is_editing": True}),
            (QueryChatMemory, "query_memory", {"memory_adapter": 'default_memory_adapter'})
        ])
        .chain(ConstructLLMMessage,
               wire_from=["query_memory", "get_message"],
               system_prompt_format=system_prompt,
               user_prompt_format=user_prompt)
        .chain(LLMChat, name="llm_chat")
        .chain(LLMToMessage)
        .parallel([
            SendIMMessage,
            (StoreMemory, {"memory_adapter": 'default_memory_adapter'}, ["get_message", "llm_chat"]),
            (ToggleEditState, {"is_editing": False})
        ])
        .build())