import aiohttp

from .openai_adapter import OpenAIAdapter, OpenAIConfig


class OfoxAIConfig(OpenAIConfig):
    api_base: str = "https://api.ofox.ai/v1"


class OfoxAIAdapter(OpenAIAdapter):
    def __init__(self, config: OfoxAIConfig):
        super().__init__(config)

    async def auto_detect_models(self) -> list[str]:
        api_url = f"{self.config.api_base}/models"
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                api_url, headers={"Authorization": f"Bearer {self.config.api_key}"}
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
                return [model["id"] for model in response_data["data"]]
