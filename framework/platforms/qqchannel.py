import botpy
from loguru import logger
from botpy.message import Message
from botpy.types.message import Reference

from constants import config


from framework.universal import handle_message
from framework.request import Request, Response
from framework.messages import ImageElement

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain

appid = config.qqchannel.appid
token = config.qqchannel.token


class Channel(botpy.Client):
    async def on_ready(self):
        logger.success(f"机器人「{self.robot.name}」启动完毕，接收消息中……")

    async def on_message_audited(self, message: Message):
        print("e")

    async def on_message_create(self, message: Message):

        last_send_text: str = ''

        async def _response_func(chain: MessageChain, text: str, voice: None, image: ImageElement):
            nonlocal last_send_text
            if text:
                last_send_text += text
                message_reference = Reference(message_id=message.id)
                await self.api.post_message(
                    channel_id=message.channel_id,
                    content=last_send_text,
                    msg_id=message.id,
                    message_reference=message_reference,
                )

            if image:
                img_bytes = await image.get_bytes()
                message_reference = Reference(message_id=message.id)
                await self.api.post_message(
                    channel_id=message.channel_id,
                    file_image=img_bytes,
                    msg_id=message.id,
                    message_reference=message_reference,
                )

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

async def start_task():
    """|coro|
    以异步方式启动
    """
    intents = botpy.Intents.all()
    client = Channel(intents=intents)
    return await client.start(appid=appid, token=token)