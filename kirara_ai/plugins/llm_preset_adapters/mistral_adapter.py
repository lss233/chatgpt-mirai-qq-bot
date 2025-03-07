import aiohttp

from kirara_ai.llm.adapter import AutoDetectModelsProtocol

from .openai_adapter import OpenAIAdapter, OpenAIConfig


class MistralConfig(OpenAIConfig):
    api_base: str = "https://api.mistral.ai/v1"


class MistralAdapter(OpenAIAdapter, AutoDetectModelsProtocol):
    def __init__(self, config: MistralConfig):
        super().__init__(config)

    async def auto_detect_models(self) -> list[str]:
        # Mistral API 响应格式:
        # {
        #   "object": "list",
        #   "data": [
        #     {
        #       "id": "string",
        #       "object": "model",
        #       "created": 0,
        #       "owned_by": "mistralai",
        #       "capabilities": {
        #         "completion_chat": true,
        #         "completion_fim": false,
        #         "function_calling": true,
        #         "fine_tuning": false,
        #         "vision": false
        #       },
        #       "name": "string",
        #       ...
        #     }
        #   ]
        # }
        api_url = f"{self.config.api_base}/models"
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                api_url, headers={"Authorization": f"Bearer {self.config.api_key}"}
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
                # 只返回支持聊天功能的模型
                return [
                    model["id"] 
                    for model in response_data["data"] 
                    if model.get("capabilities", {}).get("completion_chat", False)
                ]
