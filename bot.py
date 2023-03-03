import os
import sys

sys.path.append(os.getcwd())
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
from graia.ariadne.event.message import MessageEvent, TempMessage
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Friend, Group, Member
from graia.ariadne.message.commander import Commander
from loguru import logger

import asyncio
from utils.text_to_img import to_image
from manager.ratelimit import RateLimitManager
import time
from conversation import ConversationHandler
from middlewares.ratelimit import MiddlewareRatelimit
from constants import config, botManager
from middlewares.ratelimit import manager as ratelimit_manager

# Refer to https://graia.readthedocs.io/ariadne/quickstart/
app = Ariadne(
    ariadne_config(
        config.mirai.qq,  # 配置详见
        config.mirai.api_key,
        HttpClientConfig(host=config.mirai.http_url),
        WebsocketClientConfig(host=config.mirai.ws_url),
    ),
)


async def response_as_image(target: Union[Friend, Group], source: Source, response):
    return await app.send_message(target, await to_image(response),
                                  quote=source if config.response.quote else False)


async def response_as_text(target: Union[Friend, Group], source: Source, response):
    return await app.send_message(target, response, quote=source if config.response.quote else False)


async def response(session_id: str, target: Union[Friend, Group], source: Source, response):
    if config.text_to_image.always:
        await response_as_image(target, source, response)
    else:
        event = await response_as_text(target, source, response)
        if event.source.id < 0:
            await response_as_image(target, source, response)


async def create_timeout_task(target: Union[Friend, Group], source: Source):
    await asyncio.sleep(config.response.timeout)
    await app.send_message(target, config.response.timeout_format, quote=source if config.response.quote else False)


middlewares = [MiddlewareRatelimit()]


async def handle_rollback(target: Union[Friend, Group], session_id: str, source: Source) -> str:
    """回滚会话"""
    conversation_handler: ConversationHandler = ConversationHandler.get_handler(session_id)
    if conversation_handler.current_conversation.rollback():
        return config.response.rollback_success
    return config.response.rollback_fail


async def handle_reset(target: Union[Friend, Group], session_id: str, source: Source) -> str:
    """重置会话"""
    conversation_handler: ConversationHandler = ConversationHandler.get_handler(session_id)
    conversation_handler.current_conversation.reset()
    return config.response.reset


async def handle_keyword_preset(target: Union[Friend, Group], session_id: str, source: Source) -> str:
    pass


async def handle_message(target: Union[Friend, Group], session_id: str, message: str, source: Source) -> str:
    """正常聊天"""
    if not message.strip():
        return config.response.placeholder

    conversation_handler: ConversationHandler = await ConversationHandler.get_handler(session_id)

    def wrap_request(n, m):
        async def call(session_id, source, target, message, respond):
            await m.handle_request(session_id, source, target, message, respond, n)

        return call

    def wrap_respond(n, m):
        async def call(session_id, source, target, message, rendered, respond):
            await m.handle_respond(session_id, source, target, message, rendered, respond, n)

        return call

    async def respond(msg: str):
        await response(session_id, target, source, msg)

    async def request(a, b, c, prompt, e):
        if not conversation_handler.current_conversation:
            conversation_handler.current_conversation = await conversation_handler.create("chatgpt-web")
        async for rendered in conversation_handler.current_conversation.ask(prompt):
            if rendered:
                action = lambda session_id, source, target, prompt, rendered, respond: respond(rendered)
                for m in middlewares:
                    action = wrap_respond(action, m)

                # 开始处理 handle_response
                await action(session_id, source, target, prompt, rendered, respond)
        for m in middlewares:
            await m.handle_respond_completed(session_id, source, target, prompt, respond)

    action = request
    for m in middlewares:
        action = wrap_request(action, m)

    # 开始处理
    await action(session_id, source, target, message, respond)


@app.broadcast.receiver("FriendMessage", priority=19)
async def friend_message_listener(app: Ariadne, friend: Friend, source: Source,
                                  chain: Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]):
    if friend.id == config.mirai.qq:
        return
    if chain.display.startswith("."):
        return
    await handle_message(friend, f"friend-{friend.id}", chain.display, source)


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage", priority=19)
async def group_message_listener(group: Group, source: Source, chain: GroupTrigger):
    if chain.display.startswith("."):
        return
    await handle_message(group, f"group-{group.id}", chain.display, source)


@app.broadcast.receiver("NewFriendRequestEvent")
async def on_friend_request(event: NewFriendRequestEvent):
    if config.system.accept_friend_request:
        await event.accept()


@app.broadcast.receiver("BotInvitedJoinGroupRequestEvent")
async def on_friend_request(event: BotInvitedJoinGroupRequestEvent):
    if config.system.accept_group_invite:
        await event.accept()


@app.broadcast.receiver(AccountLaunch)
async def start_background():
    try:
        logger.info("OpenAI 服务器登录中……")
        botManager.login()
    except:
        logger.error("OpenAI 服务器失败！")
        exit(-1)
    logger.info("OpenAI 服务器登录成功")
    logger.info("尝试从 Mirai 服务中读取机器人 QQ 的 session key……")


cmd = Commander(app.broadcast)


@cmd.command(".设置 {msg_type: str} {msg_id: str} 额度为 {rate: int} 条/小时")
async def update_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member], msg_type: str, msg_id: str,
                      rate: int):
    try:
        if not sender.id == config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        if msg_type != "群组" and msg_type != "好友":
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        ratelimit_manager.update(msg_type, msg_id, rate)
        return await app.send_message(event, "额度更新成功！")
    finally:
        raise ExecutionStop()


@cmd.command(".查看 {msg_type: str} {msg_id: str} 的使用情况")
async def show_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member], msg_type: str, msg_id: str):
    try:
        if isinstance(event, TempMessage):
            return
        if not sender.id == config.mirai.manager_qq and not sender.id == int(msg_id):
            return await app.send_message(event, "您没有权限执行这个操作")
        if msg_type != "群组" and msg_type != "好友":
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        limit = ratelimit_manager.get_limit(msg_type, msg_id)
        if limit is None:
            return await app.send_message(event, f"{msg_type} {msg_id} 没有额度限制。")
        usage = ratelimit_manager.get_usage(msg_type, msg_id)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        return await app.send_message(event,
                                      f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")
    finally:
        raise ExecutionStop()


app.launch_blocking()
