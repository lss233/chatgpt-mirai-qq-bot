import re
import time
from io import BytesIO
from typing import Generator, Any, Optional

import asyncio
import httpx
from PIL import Image
from graia.ariadne.message.element import Image as GraiaImage
from loguru import logger

from accounts import AccountInfoBaseModel, account_manager
from adapter.botservice import BotAdapter
# from constants import botManager
from exceptions import BotOperationNotSupportedException


class BaiduCookieAuth(AccountInfoBaseModel):
    BDUSS: str
    """百度 Cookie 中的 BDUSS 字段"""
    BAIDUID: str
    """百度 Cookie 中的 BAIDUID 字段"""

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


def get_ts():
    return int(time.time() * 1000)


def extract_image(html):
    pattern = r'<img src="(.*?)" /><br>'
    if match := re.search(pattern, html):
        return match[1], re.sub(pattern, '', html)
    else:
        return None, html


def check_response(resp):
    if int(resp['code']) != 0:
        raise Exception(resp['msg'])


class YiyanAdapter(BotAdapter):
    """
    百度文心一言大模型
    https://yiyan.baidu.com
    """
    account: BaiduCookieAuth
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.acs_client = httpx.AsyncClient(trust_env=True)
        self.account = account_manager.pick("baidu")
        self.client = self.account.get_client()
        self.conversation_id = None
        self.parent_chat_id = ''

    async def rollback(self):
        """回滚会话"""
        raise BotOperationNotSupportedException()

    async def delete_conversation(self, session_id):
        """删除会话"""
        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/session/delete",
            json={
                "sessionId": session_id,
                "timestamp": get_ts(),
                "deviceType": "pc"
            }
        )
        req.raise_for_status()

    async def on_destoryed(self):
        """重置会话"""
        ...

    async def new_conversation(self, prompt: str):
        """创建新会话"""
        self.client.headers['Acs-Token'] = await self.get_sign()

        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/session/new",
            json={
                "sessionName": prompt,
                "timestamp": get_ts(),
                "deviceType": "pc"
            }
        )
        req.raise_for_status()
        check_response(req.json())
        return req.json()['data']['sessionId']

    async def ask(self, prompt) -> Generator[str, None, None]:
        self.client.headers['Acs-Token'] = await self.get_sign()

        if not self.conversation_id:
            self.conversation_id = await self.new_conversation(prompt)
            self.parent_chat_id = 0

        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/chat/check",
            json={
                "text": prompt,
                "timestamp": get_ts(),
                "deviceType": "pc",
            }
        )

        req.raise_for_status()
        check_response(req.json())

        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/chat/new",
            json={
                "sessionId": self.conversation_id,
                "text": prompt,
                "parentChatId": self.parent_chat_id,
                "type": 10,
                "timestamp": get_ts(),
                "deviceType": "pc",
                "code": 0,
                "msg": "",
                "sign": self.client.headers['Acs-Token']
            }
        )

        req.raise_for_status()
        check_response(req.json())

        chat_id = req.json()["data"]["botChat"]["id"]
        self.parent_chat_id = chat_id
        chat_parent_id = req.json()["data"]["botChat"]["parent"]

        sentence_id = 0
        full_response = ''
        while True:
            self.client.headers['Acs-Token'] = await self.get_sign()

            req = await self.client.post(
                url="https://yiyan.baidu.com/eb/chat/query",
                json={
                    "chatId": chat_id,
                    "parentChatId": chat_parent_id,
                    "sentenceId": sentence_id,
                    "stop": 0,
                    "timestamp": get_ts(),
                    "deviceType": "pc",
                    "sign": self.client.headers['Acs-Token']
                }
            )
            req.raise_for_status()
            check_response(req.json())

            sentence_id = req.json()["data"]["sent_id"]

            if content := req.json()["data"]["content"]:
                url, content = extract_image(content)
                if url:
                    yield GraiaImage(data_bytes=await self.__download_image(url))
                full_response = full_response + content.replace('<br>', '\n')

            logger.debug(f"[Yiyan] {self.conversation_id} - {full_response}")

            yield full_response

            await asyncio.sleep(1)

            if req.json()["data"]["is_end"] != 0 or req.json()["data"]["stop"] != 0:
                break

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role in {'assistant', 'yiyan'}:
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")

    async def get_sign(self):
        # 目前只需要这一个参数来计算 Acs-Token
        self.acs_client.headers['Cookie'] = f"BAIDUID={self.account.BAIDUID};"
        req = await self.acs_client.get("https://chatgpt-proxy.lss233.com/yiyan-api/acs")
        return req.json()['acs']

    async def __download_image(self, url: str) -> bytes:
        image = await self.client.get(url)
        image.raise_for_status()
        from_format = BytesIO(image.content)
        to_format = BytesIO()
        Image.open(from_format).save(to_format, format='png')
        return to_format.getvalue()

    @classmethod
    def register(cls):
        account_manager.register_type("baidu", BaiduCookieAuth)
