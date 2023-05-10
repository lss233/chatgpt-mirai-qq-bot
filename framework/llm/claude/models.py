from typing import Any

import httpx
from pydantic import Field

from framework.accounts import AccountInfoBaseModel


class SlackAccessTokenAuth(AccountInfoBaseModel):
    channel_id: str = Field(
        title="channel_id",
        description="负责与机器人交互的 Channel ID"
    )

    access_token: str = Field(
        title="access_token",
        description="安装 Slack App 时获得的 access_token"
    )

    app_endpoint: str = Field(
        title="app_endpoint",
        default="https://chatgpt-proxy.lss233.com/claude-in-slack/backend-api/",
        description="API 的接入点（保持默认）"
    )

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

    class Config:
        title = 'Slack 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-claude)"
        }

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client.headers['Authorization'] = f"Bearer {self.channel_id}@{self.access_token}"
        self._client.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self._client.headers[
            'User-Agent'
        ] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        self._client.headers['Sec-Fetch-User'] = '?1'
        self._client.headers['Sec-Fetch-Mode'] = 'navigate'
        self._client.headers['Sec-Fetch-Site'] = 'none'
        self._client.headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        self._client.headers['Sec-Ch-Ua-Mobile'] = '?0'
        self._client.headers['Sec-Ch-Ua'] = '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'

    def get_client(self) -> httpx.AsyncClient:
        return self._client

    async def check_alive(self) -> bool:
        """

        Successful response:
        ```
        ```
        {
            "items": []
        }
        ```
        ```
        Unsuccessful response: variety
        """
        req = await self._client.get(f"{self.app_endpoint}/conversations")
        return "items" in req.json()
