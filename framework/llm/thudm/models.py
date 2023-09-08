import httpx
from pydantic import Field

from framework.accounts import AccountInfoBaseModel


class ChatGLMAPIInfo(AccountInfoBaseModel):
    api_endpoint: str = Field(
        description="ChatGLM API 的接入点",
    )

    max_turns: int = Field(
        default=10,
        description="最大对话轮数，超过时最前面的聊天记录会被遗忘",
    )

    timeout: int = Field(
        default=120,
        description="请求超时时间（单位：秒）",
    )

    class Config:
        title = 'ChatGLM-API （离线部署版）设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-chatglm)"
        }

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.api_endpoint,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                json={}
            )
            return True
