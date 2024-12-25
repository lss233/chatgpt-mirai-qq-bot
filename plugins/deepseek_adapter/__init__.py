from framework.im.telegram.adapter import TelegramAdapter
from framework.im.telegram.config import TelegramConfig
from framework.llm.llm_registry import LLMAbility
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from deepseek_adapter.adapter import DeepSeekAdapter, DeepSeekConfig

logger = get_logger("DeepSeek")
class DeepSeekPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.llm_registry.register("deepseek", DeepSeekAdapter, DeepSeekConfig, LLMAbility.TextChat)
        logger.info("DeepSeekPlugin loaded")

    def on_start(self):
        logger.info("DeepSeekPlugin started")

    def on_stop(self):
        logger.info("DeepSeekPlugin stopped")
