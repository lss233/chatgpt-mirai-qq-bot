
from .openai_adapter import OpenAIAdapter, OpenAIConfig


class TencentCloudConfig(OpenAIConfig):
    api_base: str = "https://api.hunyuan.cloud.tencent.com/v1"


class TencentCloudAdapter(OpenAIAdapter):
    def __init__(self, config: TencentCloudConfig):
        super().__init__(config)

