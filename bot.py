import os
import sys


sys.path.append(os.getcwd())
import constants

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
from graia.ariadne.message.element import Image
from tls_client.exceptions import TLSClientExeption

from renderer.renderer import MarkdownImageRenderer, FullTextRenderer
from loguru import logger

import asyncio
from utils.text_to_img import to_image
import re
import time
from conversation import ConversationHandler
from middlewares.ratelimit import MiddlewareRatelimit
from middlewares.timeout import MiddlewareTimeout
from constants import config, botManager
from middlewares.ratelimit import manager as ratelimit_manager
from requests.exceptions import SSLError, ProxyError
from exceptions import PresetNotFoundException, BotRatelimitException, ConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, BotOperationNotSupportedException

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
    # 如果是非字符串
    if isinstance(response, Image) or isinstance(response, MessageChain):
        return await app.send_message(target, response, quote=source if config.response.quote else False)

    if config.text_to_image.always:
        await response_as_image(target, source, response)
    else:
        event = await response_as_text(target, source, response)
        if event.source.id < 0:
            await response_as_image(target, source, response)



middlewares = [MiddlewareTimeout(), MiddlewareRatelimit()]

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
        for m in middlewares:
            await m.on_respond(session_id, source, target, message, msg)

    async def request(a, b, c, prompt: str, e):
        try:
            task = None

            # 此处为会话不存在时可以执行的指令

            bot_type_search = re.search(config.trigger.switch_command, prompt)
            # 初始化会话
            if bot_type_search:
                conversation_handler.current_conversation = await conversation_handler.create(bot_type_search.group(1).strip())
                await respond(f"已切换至 {bot_type_search.group(1).strip()}，现在开始和我聊天吧！")
                return
            # 初始化会话
            elif not conversation_handler.current_conversation:
                conversation_handler.current_conversation = await conversation_handler.create("chatgpt-web")

            # 此处为会话存在后可执行的指令

            # 重置会话
            if prompt in config.trigger.reset_command:
                task = conversation_handler.current_conversation.reset()

            # 回滚会话
            elif prompt in config.trigger.rollback_command:
                task = conversation_handler.current_conversation.rollback()

            elif prompt in config.trigger.image_only_command:
                conversation_handler.current_conversation.renderer = MarkdownImageRenderer()
                await respond(f"已切换至纯图片模式，接下来我的回复将会以图片呈现！")
                return

            elif prompt in config.trigger.text_only_command:
                conversation_handler.current_conversation.renderer = FullTextRenderer()
                await respond(f"已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")
                return

            # 加载预设
            preset_search = re.search(config.presets.command, prompt)
            if preset_search:
                logger.trace(f"{session_id} - 正在执行预设： {preset_search.group(1)}")
                async for _ in conversation_handler.current_conversation.reset(): ...
                task = conversation_handler.current_conversation.load_preset(preset_search.group(1))
            elif not conversation_handler.current_conversation.preset:
                # 当前没有预设
                logger.trace(f"{session_id} - 未检测到预设，正在执行默认预设……")
                # 隐式加载不回复预设内容
                async for _ in conversation_handler.current_conversation.load_preset('default'): ...

            # 没有任务那就聊天吧！
            if not task:
                task = conversation_handler.current_conversation.ask(prompt)
            async for rendered in task:
                if rendered:
                    action = lambda session_id, source, target, prompt, rendered, respond: respond(rendered)
                    for m in middlewares:
                        action = wrap_respond(action, m)

                    # 开始处理 handle_response
                    await action(session_id, source, target, prompt, rendered, respond)
            for m in middlewares:
                await m.handle_respond_completed(session_id, source, target, prompt, respond)
        except BotOperationNotSupportedException:
            await respond("暂不支持此操作，抱歉！")
        except ConcurrentMessageException as e: # Chatbot 账号同时收到多条消息
            await respond(config.response.error_request_concurrent_error)
        except BotRatelimitException as e: # Chatbot 账号限流
            await respond(config.response.error_request_too_many.format(exc=e, remaining=e.estimated_at))
        except NoAvailableBotException: # 预设不存在
            await respond("没有账号，不支持使用此 AI！")
        except BotTypeNotFoundException as e: # 预设不存在
            await respond(f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n* chatgpt-web - ChatGPT 网页版\n* chatgpt-api - ChatGPT API版\n* bing - 微软 Bing 聊天机器人\n")
        except PresetNotFoundException: # 预设不存在
            await respond("预设不存在，请检查你的输入是否有问题！")
        except (TLSClientExeption, SSLError, ProxyError) as e: # 网络异常
            await respond(config.response.error_network_failure.format(exc=e))
        except Exception as e: # 未处理的异常
            logger.exception(e)
            await respond(config.response.error_format.format(exc=e))

    action = request
    for m in middlewares:
        action = wrap_request(action, m)

    # 开始处理
    await action(session_id, source, target, message.strip(), respond)


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
    await to_image("$$mc^2$$ test")
    try:
        logger.info("OpenAI 服务器登录中……")
        botManager.login()
    except:
        logger.error("OpenAI 服务器登录失败！")
        exit(-1)
    logger.info("OpenAI 服务器登录成功")
    logger.info("尝试从 Mirai 服务中读取机器人 QQ 的 session key……")


cmd = Commander(app.broadcast)

@cmd.command(".重新加载配置文件")
async def update_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if not sender.id == config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        constants.config = config.load_config()
        await app.send_message(event, "配置文件重新载入完毕！")
        await app.send_message(event, "重新登录账号中，详情请看控制台日志……")
        botManager.login()
        await app.send_message(event, "登录结束")
    finally:
        raise ExecutionStop()

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
        if not sender.id == config.mirai.manager_qq or not sender.id == int(msg_id):
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
