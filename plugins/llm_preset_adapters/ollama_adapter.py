from pydantic import ConfigDict, BaseModel
import requests
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.logger import get_logger

class OllamaConfig(BaseModel):
    api_base: str = "http://localhost:11434"
    model_config = ConfigDict(frozen=True)

class OllamaAdapter(LLMBackendAdapter):
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.logger = get_logger("OllamaAdapter")

    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        api_url = f"{self.config.api_base}/api/chat"
        headers = {
            "Content-Type": "application/json"
        }

        # 将消息转换为 Ollama 格式
        messages = []
        for msg in req.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        data = {
            "model": req.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": req.temperature,
                "top_p": req.top_p,
                "num_predict": req.max_tokens,
                "stop": req.stop
            }
        }

        # Remove None fields
        data = {k: v for k, v in data.items() if v is not None}
        if "options" in data:
            data["options"] = {k: v for k, v in data["options"].items() if v is not None}
        
        response = requests.post(api_url, json=data, headers=headers)
        try:
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            print(f"API Response: {response.text}")
            raise e
        
        # 转换 Ollama 响应格式为标准的 LLMChatResponse 格式
        transformed_response = {
            "id": "ollama-" + req.model,
            "object": "chat.completion",
            "created": 0,
            "model": req.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_data["message"]["content"]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        return LLMChatResponse(**transformed_response) 