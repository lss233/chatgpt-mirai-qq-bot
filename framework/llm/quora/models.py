from typing import Optional, Any

from pydantic import Field

from framework.accounts import AccountInfoBaseModel

from poe import Client as PoeClient


class PoeCookieAuth(AccountInfoBaseModel):
    p_b: str = Field(
        description="登陆 poe.com 后 Cookie 中 p_b 的值",
    )

    _client: Optional[PoeClient] = None

    class Config:
        title = 'Poe 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-poe.com)"
        }

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client = PoeClient(self.p_b)

    def get_client(self) -> PoeClient:
        return self._client

    async def check_alive(self) -> bool:
        return self._client.ws_connected
