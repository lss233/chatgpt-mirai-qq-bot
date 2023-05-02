import httpx

import constants
from framework.accounts import AccountInfoBaseModel


class BingCookieAuth(AccountInfoBaseModel):
    cookie_content: str
    """Bing 的 Cookie"""

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient(
                trust_env=True,
                headers={
                    "Cookie": self.cookie_content,
                    "sec-ch-ua": r'"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64'
                }
        ) as client:
            response = await client.get(f"{constants.config.bing.bing_endpoint}")
            return "Success" in response.text
