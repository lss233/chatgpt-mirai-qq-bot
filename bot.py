import os
import sys

from requests.exceptions import SSLError

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
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.ariadne.model import Friend, Group, Member
from graia.ariadne.message.commander import Commander, Slot, Arg
from loguru import logger

import re
import asyncio
import chatbot
from config import Config
from text_to_img import text_to_image
from manager.ratelimit import RateLimitManager
import time

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

    rate_usage = rateLimitManager.check_exceed('好友' if isinstance(target, Friend) else '群组', target.id)

    if rate_usage >= 1:
        return config.ratelimit.exceed

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

            # # 新会话
            if is_new_session:
                async for progress in session.load_conversation():
                    await app.send_message(target, progress, quote=source if config.response.quote else False)

            # 加载关键词人设
            preset_search = re.search(config.presets.command, message)
            if preset_search:
                session.reset_conversation()
                async for progress in session.load_conversation(preset_search.group(1)):
                    await app.send_message(target, progress, quote=source if config.response.quote else False)
                return config.presets.loaded_successful
            # 正常交流
            resp = await session.get_chat_response(message)
            if resp:
                logger.debug(f"{session_id} - {session.chatbot.id} {resp}")
                return resp.strip()
        except SSLError as e:
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
    ### 排队结束


@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend, source: Source,
                                  chain: Annotated[MessageChain, DetectPrefix(config.trigger.prefix)]):
    if friend.id == config.mirai.qq:
        return
    response = await handle_message(friend, f"friend-{friend.id}", chain.display, source)

    rate_usage = rateLimitManager.check_exceed('好友', friend.id)
    if rate_usage >= config.ratelimit.warning_rate:
            limit = rateLimitManager.get_limit(type, id)
            usage = rateLimitManager.get_usage(type, id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            response = response + '\n' + config.ratelimit.warning_msg.format(usage=usage['count'], limit=limit['rate'], current_time=current_time)
        
    if config.text_to_image.always:
        img = text_to_image(text=response)
        b = BytesIO()
        img.save(b, format="png")
        await app.send_message(friend, Image(data_bytes=b.getvalue()), quote=source if config.response.quote else False)
    else:
        await app.send_message(friend, response, quote=source if config.response.quote else False)


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage")
async def group_message_listener(group: Group, source: Source, chain: GroupTrigger):
    response = await handle_message(group, f"group-{group.id}", chain.display, source)

    rate_usage = rateLimitManager.check_exceed('群组', group.id)
    if rate_usage >= config.ratelimit.warning_rate:
            limit = rateLimitManager.get_limit(type, id)
            usage = rateLimitManager.get_usage(type, id)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            response = response + '\n' + config.ratelimit.warning_msg.format(usage=usage['count'], limit=limit['rate'], current_time=current_time)

    if config.text_to_image.always:
        img = text_to_image(text=response)
        b = BytesIO()
        img.save(b, format="png")
        await app.send_message(group, Image(data_bytes=b.getvalue()), quote=source if config.response.quote else False)
    else:
        event = await app.send_message(group, response, quote=source if config.response.quote else False)
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
        logger.error("OpenAI 服务器失败！")
        exit(-1)
    logger.info("OpenAI 服务器登录成功")
    logger.info("尝试从 Mirai 服务中读取机器人 QQ 的 session key……")

cmd = Commander(app.broadcast)
@cmd.command(".设置 {type} {id} 额度为 {rate} 条/小时", {"type": Slot("type", str, ""), "id": Slot("id", str, ""), "rate": Slot("rate", int, "")})
async def update_rate(sender: Union[Friend, Member], type: str, id: str, rate: int): 
    if not sender.id == config.mirai.manager_qq:
        return "您没有权限执行这个操作"
    if type != "群组" or type != "好友":
        return "类型异常，仅支持设定【群组】或【好友】的额度"
    if id != '默认' or not id.isdecimal(id):
        return "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度"
    rateLimitManager.update(type, id, rate)
    return "额度更新成功！"
    
@cmd.command(".查看 {type} {id} 的使用情况", {"type": Slot("type", str, ""), "id": Slot("id", str, "")})
async def show_rate(sender: Union[Friend, Member], type: str, id: str): 
    if not sender.id == config.mirai.manager_qq and not sender.id == int(id):
        return "您没有权限执行这个操作"
    if type != "群组" or type != "好友":
        return "类型异常，仅支持设定【群组】或【好友】的额度"
    if id != '默认' or not id.isdecimal(id):
        return "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度"
    limit = rateLimitManager.get_limit(type, id)
    usage = rateLimitManager.get_usage(type, id)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    return f"{type} {id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}"
    

app.launch_blocking()
