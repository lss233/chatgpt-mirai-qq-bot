from llm_preset_adapters.claude_adapter import ClaudeAdapter, ClaudeConfig
from llm_preset_adapters.deepseek_adapter import DeepSeekAdapter, DeepSeekConfig
from llm_preset_adapters.gemini_adapter import GeminiAdapter, GeminiConfig
from llm_preset_adapters.ollama_adapter import OllamaAdapter, OllamaConfig
from llm_preset_adapters.openai_adapter import OpenAIAdapter, OpenAIConfig

from kirara_ai.llm.llm_registry import LLMAbility
from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin

logger = get_logger("LLMPresetAdapters")


class LLMPresetAdaptersPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.llm_registry.register(
            "OpenAI", OpenAIAdapter, OpenAIConfig, LLMAbility.TextChat
        )
        self.llm_registry.register(
            "DeepSeek", DeepSeekAdapter, DeepSeekConfig, LLMAbility.TextChat
        )
        self.llm_registry.register(
            "Gemini", GeminiAdapter, GeminiConfig, LLMAbility.TextChat
        )
        self.llm_registry.register(
            "Ollama", OllamaAdapter, OllamaConfig, LLMAbility.TextChat
        )
        self.llm_registry.register(
            "Claude", ClaudeAdapter, ClaudeConfig, LLMAbility.TextChat
        )
        logger.info("LLMPresetAdaptersPlugin loaded")

    def on_start(self):
        logger.info("LLMPresetAdaptersPlugin started")

    def on_stop(self):
        logger.info("LLMPresetAdaptersPlugin stopped")
