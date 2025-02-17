from typing import Annotated, Any, Dict, Optional

from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from framework.ioc.container import DependencyContainer
from framework.llm.format.response import LLMChatResponse
from framework.logger import get_logger
from framework.memory.memory_manager import MemoryManager
from framework.memory.registry import ComposerRegistry, DecomposerRegistry, ScopeRegistry
from framework.workflow.core.block import Block, Input, Output, ParamMeta


class ChatMemoryQuery(Block):
    name = "chat_memory_query"
    inputs = {
        "chat_sender": Input(
            "chat_sender", "聊天对象", ChatSender, "要查询记忆的聊天对象"
        )
    }
    outputs = {"memory_content": Output("memory_content", "记忆内容", str, "记忆内容")}
    container: DependencyContainer

    def __init__(
        self,
        scope_type: Annotated[
            Optional[str], ParamMeta(label="级别", description="要查询记忆的级别")
        ],
    ):
        self.scope_type = scope_type

    def execute(self, chat_sender: ChatSender) -> Dict[str, Any]:
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
        entries = self.memory_manager.query(self.scope, chat_sender)
        memory_content = self.decomposer.decompose(entries)
        return {"memory_content": memory_content}


class ChatMemoryStore(Block):
    name = "chat_memory_store"

    inputs = {
        "user_msg": Input("user_msg", "用户消息", IMMessage, "用户消息", nullable=True),
        "llm_resp": Input(
            "llm_resp", "LLM 响应", LLMChatResponse, "LLM 响应", nullable=True
        ),
    }
    outputs = {}
    container: DependencyContainer

    def __init__(
        self,
        scope_type: Annotated[
            Optional[str], ParamMeta(label="级别", description="要查询记忆的级别")
        ],
    ):
        self.scope_type = scope_type
        self.logger = get_logger("Block.ChatMemoryStore")

    def execute(
        self,
        user_msg: Optional[IMMessage] = None,
        llm_resp: Optional[LLMChatResponse] = None,
    ) -> Dict[str, Any]:
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
        if user_msg is None:
            composed_messages = []
        else:
            composed_messages = [user_msg]
        if llm_resp is not None:
            if llm_resp.choices and llm_resp.choices[0].message:
                composed_messages.append(llm_resp.choices[0].message)
        if not composed_messages:
            self.logger.warning("No messages to store")
            return {}
        self.logger.debug(f"Composed messages: {composed_messages}")
        memory_entries = self.composer.compose(user_msg.sender, composed_messages)
        self.memory_manager.store(self.scope, memory_entries)

        return {}
