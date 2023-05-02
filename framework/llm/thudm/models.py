import httpx

from framework.accounts import AccountInfoBaseModel


class ChatGLMAPIInfo(AccountInfoBaseModel):
    api_endpoint: str
    """自定义 ChatGLM API 的接入点"""
    max_turns: int = 10
    """最大对话轮数"""
    timeout: int = 120
    """请求超时时间（单位：秒）"""

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.api_endpoint,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                json={}
            )
            return True
