from .openai_adapter import OpenAIAdapter, OpenAIConfig


class DeepSeekConfig(OpenAIConfig):
    api_base: str = "https://api.deepseek.com/"


class DeepSeekAdapter(OpenAIAdapter):
    def __init__(self, config: DeepSeekConfig):
        super().__init__(config)
