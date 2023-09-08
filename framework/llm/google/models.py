from typing import Any

import httpx
from pydantic import Field

from framework.accounts import AccountInfoBaseModel


class BardCookieAuth(AccountInfoBaseModel):
    cookie_content: str = Field(
        title="cookie_content",
        description="Bard 的 Cookie"
    )

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

    class Config:
        title = 'Bard 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-google-bard)"
        }

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client.headers['Cookie'] = self.cookie_content
        self._client.headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
        self._client.headers[
            'User-Agent'
        ] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'

    def get_client(self) -> httpx.AsyncClient:
        return self._client

    async def check_alive(self) -> bool:
        response = await self._client.get(
            "https://bard.google.com/?hl=en",
            timeout=30,
            follow_redirects=True,
        )
        return "SNlM0e" in response.text
