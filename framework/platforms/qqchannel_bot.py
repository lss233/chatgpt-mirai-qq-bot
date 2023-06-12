# QQ频道库
import botpy
from loguru import logger
from botpy.message import Message
from botpy.types.message import Reference
# 项目框架
from constants import config
from framework.universal import handle_message
from framework.request import Request, Response
from framework.messages import ImageElement
from framework.utils.text_to_img import to_image
# Ariadne框架
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain


class Config:
    appid = config.qqchannel.appid
    token = config.qqchannel.token


async def post_response_function(client, channel_id, message_id, text=None, image=None):
    message_reference = Reference(message_id=message_id)
    if text:
        await client.api.post_message(
            channel_id=channel_id,
            content=text,
            msg_id=message_id,
            message_reference=message_reference,
        )
    if image:
        img_bytes = await image.get_bytes()
        await client.api.post_message(
            channel_id=channel_id,
            file_image=img_bytes,
            msg_id=message_id,
        )


class Channel(botpy.Client):
    async def on_ready(self):
        logger.success(f"机器人「{self.robot.name}」启动完毕，接收消息中……")

    async def on_message_audited(self, message: Message):
        logger.warning(f"机器人「{self.robot.name}」收到了一条审核消息.")

    async def on_at_message_create(self, message: Message):

        last_send_text: str = ''

        if message.author.bot:
            return

        async def _response_func(chain: MessageChain, text: str, voice: None, image: ImageElement):
            nonlocal last_send_text
            # 如果开启了强制转图片
            if config.text_to_image.always:
                await post_response_function(
                    self,
                    message.channel_id,
                    message.id,
                    image=await to_image(text),
                )
                last_send_text = ''
            else:
                if text:
                    last_send_text += text
                    await post_response_function(self, message.channel_id, message.id, text=text)
                if image:
                    await post_response_function(self, message.channel_id, message.id, image=image)
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
    intents = botpy.Intents(public_guild_messages=True, direct_message=True, guilds=True, message_audit=True)
    client = Channel(intents=intents)
    return await client.start(appid=Config.appid, token=Config.token)
