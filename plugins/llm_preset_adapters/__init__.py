from framework.llm.llm_registry import LLMAbility
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from llm_preset_adapters.gemini_adapter import GeminiAdapter, GeminiConfig
from llm_preset_adapters.deepseek_adapter import DeepSeekAdapter, DeepSeekConfig
from llm_preset_adapters.openai_adapter import OpenAIAdapter, OpenAIConfig

logger = get_logger("LLMPresetAdapters")
class LLMPresetAdaptersPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.llm_registry.register("openai", OpenAIAdapter, OpenAIConfig, LLMAbility.TextChat)
        self.llm_registry.register("deepseek", DeepSeekAdapter, DeepSeekConfig, LLMAbility.TextChat)
        self.llm_registry.register("gemini", GeminiAdapter, GeminiConfig, LLMAbility.TextChat)
        logger.info("LLMPresetAdaptersPlugin loaded")

    def on_start(self):
        logger.info("LLMPresetAdaptersPlugin started")

    def on_stop(self):
        logger.info("LLMPresetAdaptersPlugin stopped")
