from framework.workflow.core.block.registry import BlockRegistry
from framework.workflow.implementations.blocks.im.basic import ExtractChatSender
from framework.workflow.implementations.blocks.llm.image import SimpleStableDiffusionWebUI
from framework.workflow.implementations.blocks.memory.clear_memory import ClearMemory
from framework.workflow.implementations.blocks.system.basic import TextBlock
from .im.messages import GetIMMessage, SendIMMessage
from .im.states import ToggleEditState
from .memory.chat_memory import ChatMemoryQuery, ChatMemoryStore
from .llm.chat import ChatMessageConstructor, ChatCompletion, ChatResponseConverter
from .game.dice import DiceRoll
from .game.gacha import GachaSimulator
from .system.help import GenerateHelp

def register_system_blocks(registry: BlockRegistry):
    """注册系统自带的 block"""
    # 基础 blocks
    registry.register("text_block", "internal", TextBlock, "基础：文本")
    
    # IM 相关 blocks
    registry.register("get_message", "internal", GetIMMessage, "IM: 获取最新消息")
    registry.register("send_message", "internal", SendIMMessage, "IM: 发送消息")
    registry.register("toggle_edit_state", "internal", ToggleEditState, "IM: 切换编辑状态")
    registry.register("extract_chat_sender", "internal", ExtractChatSender, "IM: 提取消息发送者")
    
    # LLM 相关 blocks
    registry.register("chat_memory_query", "internal", ChatMemoryQuery, "LLM: 查询记忆")
    registry.register("chat_message_constructor", "internal", ChatMessageConstructor, "LLM: 构造对话记录")
    registry.register("chat_completion", "internal", ChatCompletion, "LLM: 执行对话")
    registry.register("chat_response_converter", "internal", ChatResponseConverter, "LLM->IM: 转换消息")
    registry.register("chat_memory_store", "internal", ChatMemoryStore, "LLM: 存储记忆")
    
    # 画图相关 blocks
    registry.register("simple_stable_diffusion_webui", "internal", SimpleStableDiffusionWebUI, "画图: 简单 Stable Diffusion WebUI")
    
    # 游戏相关 blocks
    registry.register("dice_roll", "game", DiceRoll, "游戏: 掷骰子")
    registry.register("gacha_simulator", "game", GachaSimulator, "游戏: 抽卡模拟")
    
    # 系统相关 blocks
    registry.register("generate_help", "system", GenerateHelp, "系统: 生成帮助") 
    registry.register("clear_memory", "system", ClearMemory, "系统: 清空记忆")