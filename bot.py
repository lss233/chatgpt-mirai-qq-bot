import os, sys
sys.path.append(os.getcwd())

import utils.exithooks
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
from graia.ariadne.event.lifecycle import AccountLaunch
from loguru import logger

import re
import asyncio
import chatbot
from config import Config
from text_to_img import text_to_image


config = Config.load_config()
# Refer to https://graia.readthedocs.io/ariadne/quickstart/
app = Ariadne(
    ariadne_config(
        config.mirai.qq,  # 配置详见
        config.mirai.api_key,
        HttpClientConfig(host=config.mirai.http_url),
        WebsocketClientConfig(host=config.mirai.ws_url),
    ),
)

async def create_timeout_task(target: Union[Friend, Group], source: Source):
    await asyncio.sleep(config.response.timeout)
    await app.send_message(target, config.response.timeout_format, quote=source if config.response.quote else False)

async def handle_message(target: Union[Friend, Group], session_id: str, message: str, source: Source) -> str:
    if not message.strip():
        return config.response.placeholder
    
    timeout_task = asyncio.create_task(create_timeout_task(target, source))
    try:
        session = chatbot.get_chat_session(session_id)

        # 加载预设
        preset_search = re.search(config.presets.command, message)
        if preset_search:
            return session.load_conversation(preset_search.group(1))
        
        # 重置会话
        if message.strip() in config.trigger.reset_command:
            session.reset_conversation()
            return config.response.reset
                    
        # 回滚
        if message.strip() in config.trigger.rollback_command:
            resp = session.rollback_conversation()
            if resp:
                return config.response.rollback_success + '\n' + resp
            return config.response.rollback_fail

        
        # 正常交流
        resp = await session.get_chat_response(message)
        if resp:
            logger.debug(f"{session_id} - {resp}")
            return resp.strip()
    except Exception as e:
        if "Too many requests" in str(e):
            return config.response.request_too_fast
        logger.exception(e)
        return config.response.error_format.format(exc=e)
    finally:
        timeout_task.cancel()

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

@app.broadcast.receiver(AccountLaunch)
async def start_background(loop: asyncio.AbstractEventLoop):
    try:
        logger.info("OpenAI 服务器登录中……")
        chatbot.setup()
    except Exception as e:
        # Fail-through
        raise e
    logger.info("OpenAI 服务器登录成功")
    logger.info("尝试连接到 Mirai 服务……")
    
app.launch_blocking()
