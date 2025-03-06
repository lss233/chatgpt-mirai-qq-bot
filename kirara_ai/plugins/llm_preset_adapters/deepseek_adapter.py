from .openai_adapter import OpenAIAdapter, OpenAIConfig
import requests
from kirara_ai.llm.adapter import AutoDetectModelsProtocol, LLMBackendAdapter
from kirara_ai.llm.format.request import LLMChatRequest
from kirara_ai.llm.format.response import LLMChatResponse
from kirara_ai.logger import get_logger
from pydantic import BaseModel, ConfigDict
from openai import OpenAI
import aiohttp

class DeepSeekConfig(OpenAIConfig):
    api_base: str = "https://api.deepseek.com/"
    model_config = ConfigDict(frozen=True)
    # TODO: Add your DeepSeek API key here
    api_key = "sk-bcfcc45a678c4a2ca4c15d33a6fc977b"

class DeepSeekAdapter(OpenAIAdapter):
    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self.logger = get_logger("DeepSeekAdapter")

    
    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        client = OpenAI(api_key=self.config.api_key, base_url=self.config.api_base)
        headers = {"Content-Type": "application/json"}

        # 将消息转换为 DeepSeek 格式
        messages = []
        for msg in req.messages:
            messages.append({"role": msg.role, "content": msg.content})
        try:
            response = client.chat.completions.create(
                model=req.model or "deepseek-chat",
                messages=messages,
                max_tokens=req.max_tokens or 1024,
                temperature=req.temperature or 0.7,
                stream=False
            )
            response_data = response.choices[0].message.content
        except Exception as e:
            response_data = ""
            print(f"API Response error")
            raise e

        # 转换 Ollama 响应格式为标准的 LLMChatResponse 格式
        transformed_response = {
            "id": "deepseek-" + req.model,
            "object": "chat.completion",
            "created": 0,
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_data,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

        return LLMChatResponse(**transformed_response)

    async def auto_detect_models(self) -> list[str]:
        api_url = f"{self.config.api_base}/api/tags"
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(api_url) as response:
                response.raise_for_status()
                response_data = await response.json()
                return [tag["name"] for tag in response_data]
