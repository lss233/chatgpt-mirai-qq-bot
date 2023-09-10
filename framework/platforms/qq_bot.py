import botpy
from botpy.message import Message, DirectMessage
from botpy.types.message import Reference
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger

from constants import config
from framework.messages import ImageElement
from framework.request import Request, Response
from framework.universal import handle_message
from framework.utils.text_to_img import to_image


async def post_response_function(client, message: Message, text=None, image=None):
    send_payload = {
        'msg_id': message.id
    }

    if isinstance(message, DirectMessage):
        send_func = client.api.post_dms
        send_payload['guild_id'] = message.guild_id
        send_payload['message_reference'] = Reference(message_id=message.id, ignore_get_message_error=True)
    else:
        send_func = client.api.post_message
        send_payload['channel_id'] = message.channel_id

    if text:
        send_payload['content'] = text.replace('.', ' . ')
    if image:
        send_payload['file_image'] = await image.get_bytes()
    await send_func(**send_payload)


class QQRobotClient(botpy.Client):
    async def on_ready(self):
        logger.success(f"机器人「{self.robot.name}」启动完毕，接收消息中……")

    async def on_message_audited(self, message: Message):
        logger.warning(f"机器人「{self.robot.name}」收到了一条审核消息.")

    async def on_direct_message_create(self, message: Message):
        await self.on_at_message_create(message)

    async def on_at_message_create(self, message: Message):

        last_send_text: str = ''

        msg_str = message.content
        if not isinstance(message, DirectMessage):
            msg_str = msg_str.replace(f"<@!{message.mentions[0].id}>", "").strip()

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
                    await post_response_function(self, message, text=text)
                if image:
                    await post_response_function(self, message, image=image)
                last_send_text = ''

        request = Request()
        if isinstance(message, DirectMessage):
            request.session_id = f'好友-{message.author.id}'
        else:
            request.session_id = f'群组-{message.guild_id}'
        request.user_id = message.author.id
        request.group_id = message.guild_id
        request.nickname = message.author.username
        request.message = MessageChain([Plain(msg_str)])
        response = Response(_response_func)

        try:
            await handle_message(request, response)
        except Exception as e:
            logger.error(e)


async def start_task():
    intents = botpy.Intents(
        public_guild_messages=True,
        direct_message=True,
        guilds=True,
        message_audit=True)
    client = QQRobotClient(intents=intents)
    return await client.start(appid=config.qqrobot.appid, token=config.qqrobot.token)
