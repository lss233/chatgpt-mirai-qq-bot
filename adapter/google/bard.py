from typing import Generator, Any

from accounts import account_manager, AccountInfoBaseModel
from adapter.botservice import BotAdapter
from config import BardCookiePath
from exceptions import BotOperationNotSupportedException
from loguru import logger
import json
import httpx
from urllib.parse import quote


class BardCookieAuth(AccountInfoBaseModel):
    cookie_content: str
    """Bard 的 Cookie"""

    _client: httpx.AsyncClient = httpx.AsyncClient(trust_env=True)

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


class BardAdapter(BotAdapter):
    account: BardCookieAuth

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.at = None
        self.session_id = session_id
        self.account = account_manager.pick('bard-cookie')
        self.client = self.account.get_client()
        self.bard_session_id = ""
        self.r = ""
        self.rc = ""

    async def get_at_token(self):
        response = await self.client.get(
            "https://bard.google.com/?hl=en",
            timeout=30,
            follow_redirects=True,
        )
        self.at = quote(response.text.split('"SNlM0e":"')[1].split('","')[0])

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_destoryed(self):
        ...

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        if not self.at:
            await self.get_at_token()
        try:
            url = "https://bard.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
            # Goolge's RPC style: https://kovatch.medium.com/deciphering-google-batchexecute-74991e4e446c
            response = await self.client.post(
                url,
                timeout=30,
                params={
                    "f.req": json.dumps([None, json.dumps([[prompt], None, [self.bard_session_id, self.r, self.rc]])]),
                    "at": self.at
                }
            )
            if response.status_code != 200:
                logger.error(f"[Bard] 请求出现错误，状态码: {response.status_code}")
                logger.error(f"[Bard] {response.text}")
                raise Exception("Authentication failed")
            res = response.text.split("\n")
            for lines in res:
                if "wrb.fr" in lines:
                    txt = ""
                    data = json.loads(json.loads(lines)[0][2])
                    result = data[0][0]
                    self.bard_session_id = data[1][0]
                    self.r = data[1][1]  # 用于下一次请求, 这个位置是固定的
                    # self.rc = data[4][1][0]
                    for check in data:
                        if not check:
                            continue
                        try:
                            for element in [element for row in check for element in row]:
                                if "rc_" in element:
                                    self.rc = element
                                    break
                        except Exception:
                            continue
                    logger.debug(f"[Bard] {self.bard_session_id} - {self.r} - {self.rc} - {result}")
                    yield result
                    break

        except Exception as e:
            logger.exception(e)
            yield "[Bard] 出现了些错误"
            return

    @classmethod
    def register(cls):
        account_manager.register_type("bard", BardCookieAuth)
