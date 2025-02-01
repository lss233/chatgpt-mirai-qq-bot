from framework.llm.llm_registry import LLMAbility
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from preset_llm_adapters.gemini_adapter import GeminiAdapter, GeminiConfig
from preset_llm_adapters.deepseek_adapter import DeepSeekAdapter, DeepSeekConfig

logger = get_logger("PresetLLMAdapters")
class PresetLLMAdaptersPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.llm_registry.register("deepseek", DeepSeekAdapter, DeepSeekConfig, LLMAbility.TextChat)
        self.llm_registry.register("gemini", GeminiAdapter, GeminiConfig, LLMAbility.TextChat)
        logger.info("PresetLLMAdaptersPlugin loaded")

    def on_start(self):
        logger.info("PresetLLMAdaptersPlugin started")

    def on_stop(self):
        logger.info("PresetLLMAdaptersPlugin stopped")
