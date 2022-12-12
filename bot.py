import os, sys
sys.path.append(os.getcwd())

from charset_normalizer import from_bytes
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import (
    HttpClientConfig,
    WebsocketClientConfig,
    config as ariadne_config,
)
from graia.ariadne.message import Source
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.base import DetectPrefix, MentionMe
from typing_extensions import Annotated
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group
import chatbot
from loguru import logger
from config import Config
import json
from text_to_img import text_to_image
from io import BytesIO

with open("config.json", "rb") as f:
    guessed_json = from_bytes(f.read()).best()
    if not guessed_json:
        raise ValueError("无法识别 JSON 格式!")
    
    config = Config.parse_obj(json.loads(str(guessed_json)))

# Refer to https://graia.readthedocs.io/ariadne/quickstart/
app = Ariadne(
    ariadne_config(
        config.mirai.qq,  # 你的机器人的 qq 号
        config.mirai.api_key,  # 填入 VerifyKey
        HttpClientConfig(host=config.mirai.http_url),
        WebsocketClientConfig(host=config.mirai.ws_url),
    ),
)

async def handle_message(id: str, message: str) -> str:
    if not message.strip():
        return config.response.placeholder
    bot = chatbot.bot
    session = chatbot.get_chat_session(id)
    if message.strip() in config.trigger.reset_command:
        session.reset_conversation()
        return config.response.reset
    if message.strip() in config.trigger.rollback_command:
        if session.rollback_conversation():
            return config.response.rollback_success
        else:
            return config.response.rollback_fail
    try:
        resp = await session.get_chat_response(message)
        print(id, resp)
        return resp["message"]
    except Exception as e:
        # session.reset_conversation()
        bot.refresh_session()
        logger.error(e)
        return config.response.error_format.format(exc=e)



@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend, source: Source, chain: Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]):
    if friend.id == config.mirai.qq:
        return
    response = await handle_message(id=f"friend-{friend.id}", message=chain.display)
    await app.send_message(friend, response, quote=source if config.response.quote else False)

GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(config.trigger.prefix)] if config.trigger.require_mention != "none" else Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]

@app.broadcast.receiver("GroupMessage")
async def group_message_listener(group: Group, source: Source, chain: GroupTrigger):
    response = await handle_message(id=f"group-{group.id}", message=chain.display)
    event = await app.send_message(group,  response)
    if(event.source.id < 0):
        img = text_to_image(text=response)
        b = BytesIO()
        img.save(b, format="png")
        await app.send_message(group, Image(data_bytes=b.getvalue()), quote=source if config.response.quote else False)

app.launch_blocking()
