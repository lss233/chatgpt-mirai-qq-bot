from framework.workflow.core.block.registry import BlockRegistry
from .im.messages import GetIMMessage, SendIMMessage
from .im.states import ToggleEditState
from .memory.chat_memory import ChatMemoryQuery, ChatMemoryStore
from .llm.chat import ChatMessageConstructor, ChatCompletion, ChatResponseConverter
from .game.dice import DiceRoll
from .game.gacha import GachaSimulator
from .system.help import GenerateHelp

def register_system_blocks(registry: BlockRegistry):
    """注册系统自带的 block"""
    # IM 相关 blocks
    registry.register("get_message", "internal", GetIMMessage)
    registry.register("send_message", "internal", SendIMMessage)
    registry.register("toggle_edit_state", "internal", ToggleEditState)
    
    # LLM 相关 blocks
    registry.register("chat_memory_query", "internal", ChatMemoryQuery)
    registry.register("chat_message_constructor", "internal", ChatMessageConstructor)
    registry.register("chat_completion", "internal", ChatCompletion)
    registry.register("chat_response_converter", "internal", ChatResponseConverter)
    registry.register("chat_memory_store", "internal", ChatMemoryStore)
    
    # 游戏相关 blocks
    registry.register("dice_roll", "game", DiceRoll)
    registry.register("gacha_simulator", "game", GachaSimulator)
    
    # 系统相关 blocks
    registry.register("generate_help", "system", GenerateHelp) 