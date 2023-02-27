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
from graia.ariadne.model import Friend, Group
from graia.broadcast.exceptions import ExecutionStop
from requests.exceptions import SSLError, ProxyError
from graia.ariadne.model import Friend, Group, Member
from graia.ariadne.message.commander import Commander, Slot, Arg
from loguru import logger

import re
import asyncio
import chatbot
from config import Config
from utils.text_to_img import to_image
from manager.ratelimit import RateLimitManager
import time
from revChatGPT.V1 import Error as V1Error
import datetime

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

rateLimitManager = RateLimitManager()


async def create_timeout_task(target: Union[Friend, Group], source: Source):
    await asyncio.sleep(config.response.timeout)
    await app.send_message(target, config.response.timeout_format, quote=source if config.response.quote else False)


async def handle_message(target: Union[Friend, Group], session_id: str, message: str, source: Source) -> str:
    if not message.strip():
        return config.response.placeholder

    timeout_task = None

    session, is_new_session = chatbot.get_chat_session(session_id)

    # 回滚
    if message.strip() in config.trigger.rollback_command:
        resp = session.rollback_conversation()
        if resp:
            return config.response.rollback_success
        return config.response.rollback_fail

    # 队列满时拒绝新的消息
    if 0 < config.response.max_queue_size < session.chatbot.queue_size:
        return config.response.queue_full
    else:
        # 提示用户：请求已加入队列
        if session.chatbot.queue_size > config.response.queued_notice_size:
            await app.send_message(target, config.response.queued_notice.format(queue_size=session.chatbot.queue_size),
                                   quote=source if config.response.quote else False)

    # 以下开始需要排队

    async with session.chatbot:
        try:

            timeout_task = asyncio.create_task(create_timeout_task(target, source))

            # 重置会话
            if message.strip() in config.trigger.reset_command:
                session.reset_conversation()
                return config.response.reset

            # 加载关键词人设
            preset_search = re.search(config.presets.command, message)
            if preset_search:
                session.reset_conversation()
                async for progress in session.load_conversation(preset_search.group(1)):
                    await app.send_message(target, progress, quote=source if config.response.quote else False)
                return config.presets.loaded_successful
            elif is_new_session:
                # 新会话
                async for _ in session.load_conversation():
                    # await app.send_message(target, progress, quote=source if config.response.quote else False)
                    pass

            # 正常交流
            resp = await session.get_chat_response(message)
            if resp:
                logger.debug(f"{session_id} - {session.chatbot.id} {resp}")
                return resp.strip()
        except V1Error as e:
            # Rate limit
            if e.code == 2:
                current_time = datetime.datetime.now()
                session.chatbot.refresh_accessed_at()
                first_accessed_at = session.chatbot.accessed_at[0] if len(session.chatbot.accessed_at) > 0 \
                    else current_time - datetime.timedelta(hours=1)
                remaining = divmod(current_time - first_accessed_at, datetime.datetime.timedelta(60))
                minute = remaining[0]
                second = remaining[1].seconds
                return config.response.error_request_too_many.format(exc=e, remaining=f"{minute}分{second}秒")
            if e.code == 1:
                return config.response.error_server_overloaded.format(exc=e)
            if e.code == 4 or e.code == 5:
                return config.response.error_session_authenciate_failed.format(exc=e)
            return config.response.error_format.format(exc=e)
        except (SSLError, ProxyError) as e:
            logger.exception(e)
            return config.response.error_network_failure.format(exc=e)
        except Exception as e:
            # Other un-handled exceptions
            if 'Too many requests' in str(e):
                return config.response.error_request_too_many.format(exc=e)
            elif 'overloaded' in str(e):
                return config.response.error_server_overloaded.format(exc=e)
            elif 'Unauthorized' in str(e):
                return config.response.error_session_authenciate_failed.format(exc=e)
            logger.exception(e)
            return config.response.error_format.format(exc=e)
        else:
            # 更新额度
            rateLimitManager.increment_usage('好友' if isinstance(target, Friend) else '群组', target.id)
        finally:
            if timeout_task:
                timeout_task.cancel()
    # 排队结束


@app.broadcast.receiver("FriendMessage", priority=19)
async def friend_message_listener(app: Ariadne, friend: Friend, source: Source,
                                  chain: Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]):
    if friend.id == config.mirai.qq:
        return
    if chain.display.startswith("."):
        return
    rate_usage = rateLimitManager.check_exceed('好友', friend.id)
    if rate_usage >= 1:
        response = config.ratelimit.exceed
    else:
        response = await handle_message(friend, f"friend-{friend.id}", chain.display, source)
        if rate_usage >= config.ratelimit.warning_rate:
            limit = rateLimitManager.get_limit('好友', friend.id)
            usage = rateLimitManager.get_usage('好友', friend.id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            response = response + '\n' + config.ratelimit.warning_msg.format(usage=usage['count'], limit=limit['rate'],
                                                                             current_time=current_time)

    if config.text_to_image.always:
        await app.send_message(friend, await asyncio.get_event_loop().run_in_executor(None, to_image, response),
                               quote=source if config.response.quote else False)
    else:
        await app.send_message(friend, response, quote=source if config.response.quote else False)


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage", priority=19)
async def group_message_listener(group: Group, source: Source, chain: GroupTrigger):
    if chain.display.startswith("."):
        return
    rate_usage = rateLimitManager.check_exceed('群组', group.id)
    if rate_usage >= 1:
        return config.ratelimit.exceed
    else:
        response = await handle_message(group, f"group-{group.id}", chain.display, source)
        if rate_usage >= config.ratelimit.warning_rate:
            limit = rateLimitManager.get_limit('群组', group.id)
            usage = rateLimitManager.get_usage('群组', group.id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            response = response + '\n' + config.ratelimit.warning_msg.format(usage=usage['count'], limit=limit['rate'],
                                                                             current_time=current_time)

    if config.text_to_image.always:
        await app.send_message(group, await asyncio.get_event_loop().run_in_executor(None, to_image, response),
                               quote=source if config.response.quote else False)
    else:
        event = await app.send_message(group, response, quote=source if config.response.quote else False)
        if event.source.id < 0:
            await app.send_message(group, await asyncio.get_event_loop().run_in_executor(None, to_image, response),
                                   quote=source if config.response.quote else False)


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
        chatbot.setup()
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
        rateLimitManager.update(msg_type, msg_id, rate)
        return await app.send_message(event, "额度更新成功！")
    finally:
        raise ExecutionStop()


@cmd.command(".查看 {msg_type: str} {msg_id: str} 的使用情况")
async def show_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member], msg_type: str, msg_id: str):
    try:
        if isinstance(event, TempMessage):
            # ignored
            return
        if not sender.id == config.mirai.manager_qq and not sender.id == int(msg_id):
            return await app.send_message(event, "您没有权限执行这个操作")
        if msg_type != "群组" and msg_type != "好友":
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        limit = rateLimitManager.get_limit(msg_type, msg_id)
        if limit is None:
            return await app.send_message(event, f"{msg_type} {msg_id} 没有额度限制。")
        usage = rateLimitManager.get_usage(msg_type, msg_id)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        return await app.send_message(event,
                                      f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")
    finally:
        raise ExecutionStop()

to_image("# Markdown\n* Text 1\n* Text 2\n * Text 3\n# Line \n* Topic")
# app.launch_blocking()
