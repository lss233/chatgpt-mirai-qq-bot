import asyncio
import ctypes
import time
from typing import Generator

from adapter.botservice import BotAdapter
from config import YiyanCookiePath
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import httpx
import re

def get_ts():
    return int(time.time() * 1000)

def parse_image(html):
    pattern = r'<img src="(.*?)" /><br>'
    match = re.search(pattern, html)
    if match:
        markdown = f'![image]({match.group(1)})  \n'
        return markdown
    else:
        return html

class YiyanAdapter(BotAdapter):
    account: YiyanCookiePath
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = botManager.pick('yiyan-cookie')
        self.client = httpx.AsyncClient()
        # self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.client.headers['Cookie'] = self.account.cookie_content
        self.client.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.conversation_id = ''
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
        self.conversation_id = ""
        self.parent_chat_id = 0

    async def new_conversation(self, prompt: str):
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
        self.__check_response(req.json())
        self.conversation_id = req.json()['data']['sessionId']
        self.parent_chat_id = 0

    async def ask(self, prompt) -> Generator[str, None, None]:
        self.client.headers['Acs-Token'] = await self.get_sign()

        if not self.conversation_id:
            await self.new_conversation(prompt)

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
                "sign": await self.get_sign()
            }
        )

        req.raise_for_status()
        self.__check_response(req.json())

        chat_id = req.json()["data"]["botChat"]["id"]
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
                    "sign": await self.get_sign()
                }
            )
            req.raise_for_status()
            self.__check_response(req.json())

            await asyncio.sleep(1)

            if sentence_id != req.json()["data"]["sent_id"]:
                content = req.json()["data"]["content"]
                content = parse_image(content)
                full_response = full_response + content
                sentence_id = req.json()["data"]["sent_id"]
            yield full_response

            if req.json()["data"]["is_end"] != 0 or req.json()["data"]["stop"] != 0:
                break
        logger.debug(f"[Yiyan] {self.conversation_id} - {full_response}")

        self.parent_chat_id = chat_id

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role in ['assistant', 'yiyan']:
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")
            pass  # 不发送 AI 的回应，免得串台

    def __check_response(self, resp):
        if int(resp['code']) != 0:
            raise Exception(resp['msg'])

    async def get_sign(self):
        req = await self.client.get("https://chatgpt-proxy.lss233.com/yiyan-api/acs")
        return req.json()['acs']


