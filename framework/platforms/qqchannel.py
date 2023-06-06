import asyncio

import botpy
from loguru import logger
from botpy.message import Message
from botpy.message import MessageAudit
from constants import config

from framework.universal import handle_message
from framework.request import Request, Response

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain

appid = config.qqchannel.appid
token = config.qqchannel.token


class Channel(botpy.Client):
    async def on_ready(self):
        logger.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_message_create(self, message: Message):

        if "sleep" in message.content:
            await asyncio.sleep(10)

        request = Request()
        request.session_id = message.channel_id
        request.user_id = message.author.id
        request.group_id = message.channel_id
        request.nickname = message.author.username
        request.message = MessageChain([Plain(message.content.replace(f"<@!{message.mentions[0].id}>", "").strip())])
        logger.debug(request.message)

        response = Response(message.reply)
        try:
            await handle_message(request, response)
        except Exception as e:
            logger.error(e)
        await message.reply(content=f"机器人{self.robot.name}收到你的@消息了: {message.content}")

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