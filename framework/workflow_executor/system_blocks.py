from framework.workflow_executor.block_registry import BlockRegistry
from framework.workflows.blocks.im.messages import GetIMMessage, SendIMMessage
from framework.workflows.blocks.im.states import ToggleEditState
from framework.workflows.default.default_workflow import (
    QueryChatMemory,
    ConstructLLMMessage,
    LLMChat,
    LLMToMessage,
    StoreMemory
)

def register_system_blocks(registry: BlockRegistry):
    """注册系统自带的 block"""
    # IM 相关 blocks
    registry.register("get_message", "internal", GetIMMessage)
    registry.register("send_message", "internal", SendIMMessage)
    registry.register("toggle_edit_state", "internal", ToggleEditState)
    
    # LLM 相关 blocks
    registry.register("query_memory", "internal", QueryChatMemory)
    registry.register("construct_llm_message", "internal", ConstructLLMMessage)
    registry.register("llm_chat", "internal", LLMChat)
    registry.register("llm_to_message", "internal", LLMToMessage)
    registry.register("store_memory", "internal", StoreMemory) 