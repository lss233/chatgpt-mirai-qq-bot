import aiohttp
from pydantic import ConfigDict, BaseModel
import requests
from framework.llm.adapter import LLMBackendAdapter, AutoDetectModelsProtocol
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.logger import get_logger

class ClaudeConfig(BaseModel):
    api_key: str
    api_base: str = "https://api.anthropic.com/v1"
    model_config = ConfigDict(frozen=True)

def convert_messages_to_claude_prompt(messages) -> str:
    """将消息列表转换为 Claude 的对话格式"""
    prompt = ""
    for msg in messages:
        if msg.role == "system":
            # Claude 没有专门的系统消息，我们将其作为 Human 的第一条消息
            prompt += f"Human: {msg.content}\n\nAssistant: I understand. I'll follow these instructions.\n\n"
        elif msg.role == "user":
            prompt += f"Human: {msg.content}\n\n"
        elif msg.role == "assistant":
            prompt += f"Assistant: {msg.content}\n\n"
    # 添加最后的 Assistant: 前缀来获取回复
    prompt += "Assistant: "
    return prompt

class ClaudeAdapter(LLMBackendAdapter, AutoDetectModelsProtocol):
    def __init__(self, config: ClaudeConfig):
        self.config = config
        self.logger = get_logger("ClaudeAdapter")

    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        api_url = f"{self.config.api_base}/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # 构建请求数据
        data = {
            "model": req.model,
            "messages": [
                {
                    "role": "user" if msg.role == "user" else "assistant",
                    "content": msg.content
                }
                for msg in req.messages
                if msg.role in ["user", "assistant"]  # 跳过 system 消息，因为 Claude API 不支持
            ],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "stream": req.stream
        }

        # 如果有系统消息，将其添加到第一个用户消息前面
        system_messages = [msg for msg in req.messages if msg.role == "system"]
        if system_messages:
            if len(data["messages"]) > 0 and data["messages"][0]["role"] == "user":
                data["messages"][0]["content"] = f"{system_messages[0].content}\n\n{data['messages'][0]['content']}"

        # Remove None fields
        data = {k: v for k, v in data.items() if v is not None}
        
        response = requests.post(api_url, json=data, headers=headers)
        try:
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            self.logger.error(f"API Response: {response.text}")
            raise e

        # 转换 Claude 响应格式为标准的 LLMChatResponse 格式
        transformed_response = {
            "id": response_data.get("id", ""),
            "object": "chat.completion",
            "created": response_data.get("created_at", 0),
            "model": req.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_data["content"][0]["text"]
                },
                "finish_reason": response_data.get("stop_reason", "stop")
            }],
            "usage": {
                "prompt_tokens": 0,  # Claude API 目前不返回 token 使用量
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        return LLMChatResponse(**transformed_response) 
    
    async def auto_detect_models(self) -> list[str]:
        # {
        #   "data": [
        #     {
        #       "type": "model",
        #       "id": "claude-3-5-sonnet-20241022",
        #       "display_name": "Claude 3.5 Sonnet (New)",
        #       "created_at": "2024-10-22T00:00:00Z"
        #     }
        #   ],
        #   "has_more": true,
        #   "first_id": "<string>",
        #   "last_id": "<string>"
        # }
        api_url = f"{self.config.api_base}/models"
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(api_url, headers={"x-api-key": self.config.api_key}) as response:
                response.raise_for_status()
                response_data = await response.json()
                return [model["id"] for model in response_data["data"]]