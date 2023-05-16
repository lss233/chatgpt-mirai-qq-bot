import httpx
import json
from pydantic import Field

import constants
from framework.accounts import AccountInfoBaseModel
from framework.exceptions import LLmAuthenticationFailedException

class BingCookieAuth(AccountInfoBaseModel):
    cookie_content: str = Field(
        title="cookie_content",
        description="Bing 的 Cookie"
    )

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

    class Config:
        title = 'Bing 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-new-bing-sydney)"
        }

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient(
                trust_env=True,
                headers={
                    "Cookie": ';'.join(f"{cookie['name']}=cookie['value'])" for cookie in json.loads(self.cookie_content)),
                    "sec-ch-ua": r'"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64'
                }
        ) as client:
            response = await client.get(f"{constants.config.bing.bing_endpoint}")
            if response.json()["result"]["value"] == "UnauthorizedRequest":
                raise LLmAuthenticationFailedException(response.json()["result"]["message"])
            return "Success" in response.text
