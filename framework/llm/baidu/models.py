from typing import Any

import httpx
from pydantic import Field

from framework.accounts import AccountInfoBaseModel


class BaiduCookieAuth(AccountInfoBaseModel):
    BDUSS: str = Field(
        title="BDUSS",
        description="百度 Cookie 中的 BDUSS 字段"
    )
    BAIDUID: str = Field(
        title="BAIDUID",
        description="百度 Cookie 中的 BAIDUID 字段"
    )

    class Config:
        title = '百度 Cookie'
        schema_extra = {
            "description": "配置教程：[Wiki](https://github.com/lss233/chatgpt-mirai-qq-bot/wiki/%E6%96%87%E5%BF%83%E4%B8%80%E8%A8%80-Cookie-%E8%8E%B7%E5%8F%96%E6%95%99%E7%A8%8B)"
        }

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._client.headers['Cookie'] = f"BDUSS={self.BDUSS};"
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
        {
            "ret": 0,
            "content": {
                "isHasPhoneNumber": true,
                "firstShowAT": true,
                "isForeignPhoneNumber": false,
                "agreement": 0,
                "watermark": "___",
                "uname": "__",
                "firstPrompt": 1,
                "authStatus": 0,
                "showWatermark": true,
                "hasATAuthority": false,
                "portrait": "___",
                "isLogin": true,
                "protocol": 1,
                "fuzzyName": "___",
                "isBanned": false,
                "applyStatus": 1,
                "status": 1
            },
            "logId": "___"
        }
        ```
        Unsuccessful response:
        ```
        {
            "ret": 0,
            "content": {
                "isLogin": false,
                "isHasPhoneNumber": true,
                "isForeignPhoneNumber": false,
                "authStatus": 0,
                "portrait": ""
            },
            "logId": "___"
        }
        ```
        """
        req = await self._client.post("https://yiyan.baidu.com/eb/user/info")
        return req.json() \
            .get("content", {"isLogin": False}) \
            .get("isLogin", False)
