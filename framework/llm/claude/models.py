from typing import Any

import httpx

from framework.accounts import AccountInfoBaseModel


class SlackAccessTokenAuth(AccountInfoBaseModel):
    channel_id: str
    """负责与机器人交互的 Channel ID"""

    access_token: str
    """安装 Slack App 时获得的 access_token"""

    app_endpoint: str = "https://chatgpt-proxy.lss233.com/claude-in-slack/backend-api/"
    """API 的接入点"""

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

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

