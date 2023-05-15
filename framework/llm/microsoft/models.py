import httpx
import json
from pydantic import Field

from EdgeGPT import Chatbot as EdgeChatbot
import constants
from framework.accounts import AccountInfoBaseModel


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
        bot = None
        bot = await EdgeChatbot.create(cookies=json.loads(self.cookie_content))
        return bot is not None
        # cookie_content 的格式不可以直接作为 header，所以不能直接用 httpx 来测试
        # async with httpx.AsyncClient(
        #         trust_env=True,
        #         headers={
        #             # "Cookie": self.cookie_content,
        #             "sec-ch-ua": r'"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
        #             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64'
        #         }
        # ) as client:
        #     response = await client.get(f"{constants.config.bing.bing_endpoint}")
        #     return "Success" in response.text
