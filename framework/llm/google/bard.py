from typing import Generator, Any

import httpx

from framework.accounts import account_manager
from framework.llm.llm import Llm
from framework.exceptions import LlmOperationNotSupportedException, LlmRequestTimeoutException, \
    LlmRequestFailedException
from loguru import logger
import json
from urllib.parse import quote

from framework.llm.google.models import BardCookieAuth


class BardAdapter(Llm):
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
        raise LlmOperationNotSupportedException()

    async def on_destoryed(self):
        ...

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:
            if not self.at:
                await self.get_at_token()
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
            response.raise_for_status()
            res = response.text.split("\n")
            for lines in res:
                if "wrb.fr" in lines:
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
                        except (KeyError, ValueError):
                            continue
                    logger.debug(f"[Bard] {self.bard_session_id} - {self.r} - {self.rc} - {result}")
                    yield result
                    break
        except httpx.TimeoutException as e:
            raise LlmRequestTimeoutException("bard") from e
        except httpx.HTTPStatusError as e:
            raise LlmRequestFailedException("bard") from e

    @classmethod
    def register(cls):
        account_manager.register_type("bard", BardCookieAuth)
