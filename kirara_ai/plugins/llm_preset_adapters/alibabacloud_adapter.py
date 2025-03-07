from .openai_adapter import OpenAIAdapter, OpenAIConfig


class AlibabaCloudConfig(OpenAIConfig):
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class AlibabaCloudAdapter(OpenAIAdapter):
    def __init__(self, config: AlibabaCloudConfig):
        super().__init__(config)
    