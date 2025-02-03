from pydantic import ConfigDict, BaseModel
import requests
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse

class OpenAIConfig(BaseModel):
    api_key: str
    api_base: str = "https://api.openai.com/v1"
    model_config = ConfigDict(frozen=True)

class OpenAIAdapter(LLMBackendAdapter):
    def __init__(self, config: OpenAIConfig):
        self.config = config

    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        api_url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "messages": [msg.model_dump(mode='json') for msg in req.messages],
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

        # Remove None fields
        data = {k: v for k, v in data.items() if v is not None}
        
        response = requests.post(api_url, json=data, headers=headers)
        try:
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            print(f"API Response: {response.text}")
            raise e
        print(response_data)
        return LLMChatResponse(**response_data)
