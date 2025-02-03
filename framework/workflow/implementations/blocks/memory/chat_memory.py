from typing import Any, Dict, List, Optional
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output
from framework.memory.memory_adapter import MemoryAdapter
from framework.llm.format.response import LLMChatResponse

class ChatMemoryQuery(Block):
    def __init__(self, container: DependencyContainer, memory_adapter: str):
        inputs = {"msg": Input("msg", IMMessage, "Input message")}
        outputs = {"memory_content": Output("memory_content", str, "memory messages")}
        super().__init__("chat_memory_query", inputs, outputs)
        self.container = container
        self.memory_adapter = MemoryAdapter(container)

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        sender = msg.sender
        content = msg.content
        memory_content = self.memory_adapter.query(sender=sender, content=content)
        return {"memory_content": memory_content}

class ChatMemoryStore(Block):
    def __init__(self, container: DependencyContainer, memory_adapter: str):
        inputs = {
            "user_msg": Input("user_msg", IMMessage, "User message"),
            "llm_resp": Input("llm_resp", LLMChatResponse, "LLM response message")
        }
        outputs = {}
        super().__init__("chat_memory_store", inputs, outputs)
        self.container = container
        self.memory_adapter = MemoryAdapter(container)

    def execute(self, user_msg: IMMessage, llm_resp: LLMChatResponse) -> Dict[str, Any]:
        self.memory_adapter.store(
            sender=user_msg.sender,
            content=user_msg.content
        )
        
        self.memory_adapter.store(
            sender=llm_resp.choices[0].message.role,
            content=llm_resp.choices[0].message.content
        )
        
        return {} 