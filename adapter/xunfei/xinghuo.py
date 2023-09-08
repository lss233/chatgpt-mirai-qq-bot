from io import BytesIO

from typing import Generator

from adapter.botservice import BotAdapter
from config import XinghuoCookiePath
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import httpx
import base64
from PIL import Image


class XinghuoAdapter(BotAdapter):
    """
    Credit: https://github.com/dfvips/xunfeixinghuo
    """
    account: XinghuoCookiePath
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = botManager.pick('xinghuo-cookie')
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.client)
        self.conversation_id = None
        self.parent_chat_id = ''

    async def delete_conversation(self, session_id):
        return await self.client.post("https://xinghuo.xfyun.cn/iflygpt/u/chat-list/v1/del-chat-list", json={
            'chatListId': session_id
        })

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        await self.client.aclose()
        self.client = httpx.AsyncClient(proxies=self.account.proxy)
        self.__setup_headers(self.client)
        self.conversation_id = None
        self.parent_chat_id = 0

    def __setup_headers(self, client):
        client.headers['Cookie'] = f"ssoSessionId={self.account.ssoSessionId};"
        client.headers[
            'User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        client.headers['Sec-Fetch-User'] = '?1'
        client.headers['Sec-Fetch-Mode'] = 'navigate'
        client.headers['Sec-Fetch-Site'] = 'none'
        client.headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        client.headers['Sec-Ch-Ua-Mobile'] = '?0'
        client.headers['Sec-Ch-Ua'] = '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'
        client.headers['Origin'] = 'https://xinghuo.xfyun.cn'
        client.headers['Referer'] = 'https://xinghuo.xfyun.cn/desk'
        client.headers['Connection'] = 'keep-alive'
        client.headers['X-Requested-With'] = 'XMLHttpRequest'

    async def new_conversation(self):
        req = await self.client.post(
            url="https://xinghuo.xfyun.cn/iflygpt/u/chat-list/v1/create-chat-list",
            json={}
        )
        req.raise_for_status()
        self.__check_response(req.json())
        self.conversation_id = req.json()['data']['id']
        self.parent_chat_id = 0

    async def ask(self, prompt) -> Generator[str, None, None]:
        if not self.conversation_id:
            await self.new_conversation()

        full_response = ''
        async with self.client.stream(
                    "POST",
                    url="https://xinghuo.xfyun.cn/iflygpt-chat/u/chat_message/chat",
                    data={
                        'fd': self.account.fd,
                        'chatId': self.conversation_id,
                        'text': prompt,
                        'GtToken': self.account.GtToken,
                        'sid': self.account.sid,
                        'clientType': '1',
                        'isBot':'0'
                    },
            ) as req:
            async for line in req.aiter_lines():
                if not line:
                    continue
                if line == 'data:<end>':
                    break
                if line == 'data:[geeError]':
                    yield "错误：出现验证码，请到星火网页端发送一次消息再试。"
                    break
                encoded_data = line[len("data:"):]
                missing_padding = len(encoded_data) % 4
                if missing_padding != 0:
                    encoded_data += '=' * (4 - missing_padding)
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                if encoded_data != 'zw':
                    decoded_data = decoded_data.replace('\n\n', '\n')
                full_response += decoded_data
                yield full_response

        logger.debug(f"[Xinghuo] {self.conversation_id} - {full_response}")

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role in {'assistant', 'xinghuo'}:
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