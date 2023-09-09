from typing import Optional, Any

import httpx
from pydantic import Field

from framework.accounts import AccountInfoBaseModel


class PoeCookieAuth(AccountInfoBaseModel):
    p_b: str = Field(
        description="登陆 poe.com 后 Cookie 中 p_b 的值",
    )

    class Config:
        title = 'Poe 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-poe.com)"
        }

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://chatgpt-proxy.lss233.com/poe/v1/models',
                headers={'Authorization': f'Bearer {self.p_b}'}
            )

            return response.status_code == 200
