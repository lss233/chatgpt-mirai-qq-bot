import base64
from typing import Generator

import httpx
from loguru import logger

from framework.accounts import account_manager
from framework.exceptions import LlmOperationNotSupportedException
from framework.llm.iflytek.models import XinghuoWebCookieAuth
from framework.llm.llm import Llm


def __check_response(resp):
    if int(resp['code']) != 0:
        raise Exception(resp['msg'])


class XinghuoWebAdapter(Llm):
    """
    星火网页版
    Credit: https://github.com/dfvips/xunfeixinghuo
    """
    account: XinghuoWebCookieAuth
    client: httpx.AsyncClient

    def __init__(self, session_id: str = ""):
        super().__init__(session_id)
        self.session_id = session_id
        self.account = account_manager.pick('xinghuo-cookie')
        self.client = self.account.get_client()
        self.conversation_id = None
        self.parent_chat_id = ''

    async def delete_conversation(self, session_id):
        return await self.client.post("https://xinghuo.xfyun.cn/iflygpt/u/chat-list/v1/del-chat-list", json={
            'chatListId': session_id
        })

    async def rollback(self):
        raise LlmOperationNotSupportedException()


    async def new_conversation(self):
        req = await self.client.post(
            url="https://xinghuo.xfyun.cn/iflygpt/u/chat-list/v1/create-chat-list",
            json={}
        )
        req.raise_for_status()
        __check_response(req.json())
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
                'isBot': '0'
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
            async for item in self.ask(text):
                ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")

    @classmethod
    def register(cls):
        account_manager.register_type("xinghuo-cookie", XinghuoWebCookieAuth)
