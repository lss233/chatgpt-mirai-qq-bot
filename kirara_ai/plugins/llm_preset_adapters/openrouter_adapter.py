from .openai_adapter import OpenAIAdapter, OpenAIConfig


class OpenRouterConfig(OpenAIConfig):
    api_base: str = "https://openrouter.ai/api/v1"

class OpenRouterAdapter(OpenAIAdapter):
    def __init__(self, config: OpenRouterConfig):
        super().__init__(config)

