import asyncio

import botpy
from loguru import logger
from botpy.message import Message
from botpy.message import MessageAudit
from constants import config

from typing import Optional

from framework.universal import handle_message
from framework.request import Request, Response

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain

appid = config.qqchannel.appid
token = config.qqchannel.token


class Channel(botpy.Client):
    async def on_ready(self):
        logger.success(f"机器人「{self.robot.name}」启动完毕，接收消息中……")

    async def on_message_create(self, message: Message):

        last_message_item: Optional[Message] = None
        last_send_text: str = ''

        async def _response_func(chain: MessageChain, text: str, voice: None, image: None):
            nonlocal last_message_item, last_send_text
            if text:
                last_send_text += text
                logger.debug(f"发送文本：{last_send_text}")
                if last_message_item:
                    last_message_item = await last_message_item.edit(content=last_send_text)
                else:
                    last_message_item = await message.reply(content=last_send_text)
                last_send_text = ''

        request = Request()
        request.session_id = message.channel_id
        request.user_id = message.author.id
        request.group_id = message.channel_id
        request.nickname = message.author.username
        request.message = MessageChain([Plain(message.content.replace(f"<@!{message.mentions[0].id}>", "").strip())])

        response = Response(_response_func)

        try:
            await handle_message(request, response)
        except Exception as e:
            logger.error(e)

    async def on_message_audit_pass(self, message: MessageAudit):
        """
        此处为处理该事件的代码
        """

    async def on_message_audit_reject(self, message: MessageAudit):
        """
        此处为处理该事件的代码
        """

async def start_task():
    """|coro|
    以异步方式启动
    """
    intents = botpy.Intents.all()
    client = Channel(intents=intents)
    return await client.start(appid=appid, token=token)