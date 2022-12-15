import os, sys
sys.path.append(os.getcwd())

from io import BytesIO
from typing import Union
from typing_extensions import Annotated
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import (
    HttpClientConfig,
    WebsocketClientConfig,
    config as ariadne_config,
)
from graia.ariadne.message import Source
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.base import DetectPrefix, MentionMe
from graia.ariadne.event.mirai import NewFriendRequestEvent, BotInvitedJoinGroupRequestEvent
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group
from loguru import logger

import chatbot
from config import Config
from text_to_img import text_to_image


config = Config.load_config()
# Refer to https://graia.readthedocs.io/ariadne/quickstart/
app = Ariadne(
    ariadne_config(
        config.mirai.qq,  # 配置详见 config.json
        config.mirai.api_key,
        HttpClientConfig(host=config.mirai.http_url),
        WebsocketClientConfig(host=config.mirai.ws_url),
    ),
)

async def handle_message(target: Union[Friend, Group], session_id: str, message: str, source: Source) -> str:
    
    if not message.strip():
        return config.response.placeholder

    bot = chatbot.bot
    resp = None
    e = None

    session, is_new_session = chatbot.get_chat_session(session_id, app, target, source)
    if is_new_session:
        e = await chatbot.initial_process(session)

    if not e and message.strip() in config.trigger.reset_command:
        session.reset_conversation()
        e = await chatbot.initial_process(session)
        if not e:
            return config.response.reset
        
    if not e and message.strip() in config.trigger.rollback_command:
        return config.response.rollback_success if session.rollback_conversation() else config.response.rollback_fail

    if not e:
        resp, e = await chatbot.keyword_presets_process(session, message)
        if e:
            logger.exception(e)
        if resp:
            logger.debug(f"{session_id} - {resp}")
            return resp

    if not e:
        resp, e = await session.get_chat_response(message)
        if e:
            logger.exception(e)
        if resp:
            logger.debug(f"{session_id} - {resp}")
            return resp["message"]
        
    if e:
        refresh_task = bot.refresh_session()
        if refresh_task:
            await refresh_task
        return config.response.error_format.format(exc=e)

@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend, source: Source, chain: Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]):
    if friend.id == config.mirai.qq:
        return
    response = await handle_message(friend, f"friend-{friend.id}", chain.display, source)
    await app.send_message(friend, response, quote=source if config.response.quote else False)

GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(config.trigger.prefix)] if config.trigger.require_mention != "none" else Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]

@app.broadcast.receiver("GroupMessage")
async def group_message_listener(group: Group, source: Source, chain: GroupTrigger):
    response = await handle_message(group, f"group-{group.id}", chain.display, source)
    event = await app.send_message(group, response)
    if event.source.id < 0:
        img = text_to_image(text=response)
        b = BytesIO()
        img.save(b, format="png")
        await app.send_message(group, Image(data_bytes=b.getvalue()), quote=source if config.response.quote else False)

@app.broadcast.receiver("NewFriendRequestEvent")
async def on_friend_request(event: NewFriendRequestEvent):
    if config.system.accept_friend_request:
        await event.accept()

@app.broadcast.receiver("BotInvitedJoinGroupRequestEvent")
async def on_friend_request(event: BotInvitedJoinGroupRequestEvent):
    if config.system.accept_group_invite:
        await event.accept()

app.launch_blocking()
