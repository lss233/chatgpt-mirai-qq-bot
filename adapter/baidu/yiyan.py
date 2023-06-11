from io import BytesIO

import asyncio
import time
from typing import Generator
from graia.ariadne.message.element import Image as GraiaImage
from adapter.botservice import BotAdapter
from config import YiyanCookiePath
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import httpx
import re
from PIL import Image


def get_ts():
    return int(time.time() * 1000)


def extract_image(html):
    pattern = r'<img src="(.*?)" /><br>'
    if match := re.search(pattern, html):
        return match[1], re.sub(pattern, '', html)
    else:
        return None, html


class YiyanAdapter(BotAdapter):
    account: YiyanCookiePath
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = botManager.pick('yiyan-cookie')
        self.acs_client = httpx.AsyncClient(proxies=self.account.proxy)
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.acs_client)
        self.__setup_headers(self.client)
        self.conversation_id = None
        self.parent_chat_id = ''

    async def delete_conversation(self, session_id):
        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/session/delete",
            json={
                "sessionId": session_id,
                "timestamp": get_ts(),
                "deviceType": "pc"
            }
        )
        req.raise_for_status()

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        await self.client.aclose()
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.client)
        self.conversation_id = None
        self.parent_chat_id = 0

    def __setup_headers(self, client):
        client.headers['Cookie'] = f"BDUSS={self.account.BDUSS};"
        client.headers['Content-Type'] = 'application/json;charset=UTF-8'
        client.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        client.headers['Sec-Fetch-User'] = '?1'
        client.headers['Sec-Fetch-Mode'] = 'navigate'
        client.headers['Sec-Fetch-Site'] = 'none'
        client.headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        client.headers['Sec-Ch-Ua-Mobile'] = '?0'
        client.headers['Sec-Ch-Ua'] = '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'

    async def new_conversation(self, prompt: str):
        self.client.headers['Acs-Token'] = await self.get_sign()

        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/session/new",
            json={
                "sessionName": prompt,
                "timestamp": get_ts(),
                "plugins": [],
                "deviceType": "pc"
            }
        )
        req.raise_for_status()
        self.__check_response(req.json())
        self.conversation_id = req.json()['data']['sessionId']
        self.parent_chat_id = 0

    async def ask(self, prompt) -> Generator[str, None, None]:
        self.client.headers['Acs-Token'] = await self.get_sign()

        if not self.conversation_id:
            await self.new_conversation(prompt)

        req = await self.client.post(
            url="https://yiyan.baidu.com/eb/chat/check",
            json={
                "text": prompt,
                "timestamp": get_ts(),
                "deviceType": "pc",
            }
        )

        req.raise_for_status()
        self.__check_response(req.json())

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
                "plugins": [],
                "pluginInfo": "",
                "jt": "",
                "sign": self.client.headers['Acs-Token']
            }
        )

        req.raise_for_status()
        self.__check_response(req.json())

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
            self.__check_response(req.json())

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

    def __check_response(self, resp):
        if int(resp['code']) != 0:
            raise Exception(resp['msg'])

    async def get_sign(self):
        # 目前只需要这一个参数来计算 Acs-Token
        self.acs_client.headers['Cookie'] = f"BAIDUID={self.account.BAIDUID};"
        req = await self.acs_client.get("https://chatgpt-proxy.lss233.com/yiyan-api/acs", timeout=30)
        return req.json()['acs']

    async def __download_image(self, url: str) -> bytes:
        image = await self.client.get(url)
        image.raise_for_status()
        from_format = BytesIO(image.content)
        to_format = BytesIO()
        Image.open(from_format).save(to_format, format='png')
        return to_format.getvalue()
