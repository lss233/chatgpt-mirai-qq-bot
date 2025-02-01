from .openai_adapter import OpenAIConfig, OpenAIAdapter

class DeepSeekConfig(OpenAIConfig):
    api_base: str = "https://api.deepseek.com/"

class DeepSeekAdapter(OpenAIAdapter):
    def __init__(self, config: DeepSeekConfig):
        super().__init__(config)