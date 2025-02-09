from typing import Any, Dict, List, Optional
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output
from framework.memory.memory_manager import MemoryManager
from framework.memory.registry import ScopeRegistry, ComposerRegistry, DecomposerRegistry
from framework.llm.format.response import LLMChatResponse

class ChatMemoryQuery(Block):
    name = "chat_memory_query"
    inputs = {"msg": Input("msg", IMMessage, "Input message")}
    outputs = {"memory_content": Output("memory_content", str, "memory messages")}
    container: DependencyContainer

    def __init__(self, scope_type: Optional[str] = None):
        self.scope_type = scope_type


    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        self.memory_manager = self.container.resolve(MemoryManager)
        
        # 如果没有指定作用域类型，使用配置中的默认值
        if self.scope_type is None:
            self.scope_type = self.memory_manager.config.default_scope
            

        # 获取作用域实例
        scope_registry = self.container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(self.scope_type)
        
        # 获取解析器实例
        decomposer_registry = self.container.resolve(DecomposerRegistry)
        
        self.decomposer = decomposer_registry.get_decomposer("default")
        entries = self.memory_manager.query(self.scope, msg.sender)
        memory_content = self.decomposer.decompose(entries)
        return {"memory_content": memory_content}

class ChatMemoryStore(Block):
    name = "chat_memory_store"

    inputs = {
        "user_msg": Input("user_msg", IMMessage, "User message"),
        "llm_resp": Input("llm_resp", LLMChatResponse, "LLM response message")
    }
    outputs = {}
    container: DependencyContainer
    
    def __init__(self, scope_type: Optional[str] = None):
        self.scope_type = scope_type

    def execute(self, user_msg: IMMessage, llm_resp: LLMChatResponse) -> Dict[str, Any]:
        self.memory_manager = self.container.resolve(MemoryManager)
        

        # 如果没有指定作用域类型，使用配置中的默认值
        if self.scope_type is None:
            self.scope_type = self.memory_manager.config.default_scope
            
        # 获取作用域实例
        scope_registry = self.container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(self.scope_type)
        
        # 获取组合器实例
        composer_registry = self.container.resolve(ComposerRegistry)
        self.composer = composer_registry.get_composer("default")
        
        # 存储用户消息和LLM响应
        composed_messages = [user_msg]
        if llm_resp.choices and llm_resp.choices[0].message:
            composed_messages.append(llm_resp.choices[0].message)
        print(composed_messages)
        memory_entries = self.composer.compose(user_msg.sender, composed_messages)
        self.memory_manager.store(self.scope, memory_entries)
        
        return {} 