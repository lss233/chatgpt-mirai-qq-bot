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
from framework.workflows.blocks.game.dice import DiceRoll
from framework.workflows.blocks.game.gacha import GachaSimulator
from framework.workflows.blocks.system.help import GenerateHelp

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
    
    # 游戏相关 blocks
    registry.register("dice_roll", "game", DiceRoll)
    registry.register("gacha_simulator", "game", GachaSimulator)
    
    # 系统相关 blocks
    registry.register("generate_help", "system", GenerateHelp) 