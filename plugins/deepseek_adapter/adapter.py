from pydantic import BaseModel
import aiohttp
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse

class DeepSeekConfig(BaseModel):
    api_key: str
    api_base: str = "https://api.deepseek.com/"
    class Config:
        frozen = True

class DeepSeekAdapter(LLMBackendAdapter):
    def __init__(self, config: DeepSeekConfig):
        self.config = config


    async def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        api_url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "messages": req.messages,
            "model": req.model,
            "frequency_penalty": req.frequency_penalty,
            "max_tokens": req.max_tokens,
            "presence_penalty": req.presence_penalty,
            "response_format": req.response_format,
            "stop": req.stop,
            "stream": req.stream,
            "stream_options": req.stream_options,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "tools": req.tools,
            "tool_choice": req.tool_choice,
            "logprobs": req.logprobs,
            "top_logprobs": req.top_logprobs,
        }

        # 移除值为 None 的字段
        data = {k: v for k, v in data.items() if v is not None}
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=data, headers=headers) as response:
                response.raise_for_status()
                response_data = await response.json()
                return LLMChatResponse(**response_data)
        return LLMChatResponse(
            id=response_data["id"],
            choices=response_data["choices"],
            created=response_data["created"],
            model=response_data["model"],
            system_fingerprint=response_data["system_fingerprint"],
            object=response_data["object"],
            usage=response_data["usage"]
        )