import asyncio
import time
from universal import handle_message
import constants
from typing import Union
from typing_extensions import Annotated
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import (
    HttpClientConfig,
    WebsocketClientConfig,
    config as ariadne_config, WebsocketServerConfig,
)
from graia.amnesia.builtins.aiohttp import AiohttpServerService
from graia.ariadne.message import Source
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.base import DetectPrefix, MentionMe
from graia.ariadne.event.mirai import NewFriendRequestEvent, BotInvitedJoinGroupRequestEvent
from graia.ariadne.event.message import MessageEvent, TempMessage
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Friend, Group, Member, AriadneBaseModel
from graia.ariadne.message.commander import Commander
from graia.ariadne.message.element import Image, ForwardNode, Plain, Forward

from loguru import logger

from utils.text_to_img import to_image

from manager.bot import BotManager
from constants import config, botManager
from middlewares.ratelimit import manager as ratelimit_manager

# Refer to https://graia.readthedocs.io/ariadne/quickstart/
if config.mirai.reverse_ws_port:
    Ariadne.config(default_account=config.mirai.qq)
    app = Ariadne(
        ariadne_config(
            config.mirai.qq,  # 配置详见
            config.mirai.api_key,
            WebsocketServerConfig()
        ),
    )
    app.launch_manager.add_launchable(AiohttpServerService(config.mirai.reverse_ws_host, config.mirai.reverse_ws_port))
else:
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


FriendTrigger = Annotated[MessageChain, DetectPrefix(config.trigger.prefix + config.trigger.prefix_friend)]


@app.broadcast.receiver("FriendMessage", priority=19)
async def friend_message_listener(app: Ariadne, target: Friend, source: Source,
                                  chain: FriendTrigger):
    if target.id == config.mirai.qq:
        return
    if chain.display.startswith("."):
        return

    async def response(msg: AriadneBaseModel):
        # 如果是非字符串
        if isinstance(msg, Image) or isinstance(msg, MessageChain):
            return await app.send_message(target, msg, quote=source if config.response.quote else False)

        if config.text_to_image.always:
            return await response_as_image(target, source, msg)
        else:
            event = await response_as_text(target, source, msg)
            if event.source.id < 0:
                return await response_as_image(target, source, msg)

    await handle_message(
        response,
        f"friend-{target.id}",
        chain.display,
        chain,
        is_manager=target.id == config.mirai.manager_qq
    )


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix + config.trigger.prefix_group)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage", priority=19)
async def group_message_listener(target: Group, source: Source, chain: GroupTrigger, member: Member):
    if chain.display.startswith("."):
        return

    async def response(msg: AriadneBaseModel):
        # 如果是非字符串
        if isinstance(msg, Image) or isinstance(msg, MessageChain):
            return await app.send_message(target, msg, quote=source if config.response.quote else False)

        if config.text_to_image.always:
            return await response_as_image(target, source, msg)
        else:
            event = await response_as_text(target, source, msg)
            if event.source.id < 0:
                return await response_as_image(target, source, msg)

    await handle_message(
        response,
        f"group-{target.id}",
        chain.display,
        chain,
        is_manager=member.id == config.mirai.manager_qq
    )


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
        await botManager.login()
    except:
        logger.error("OpenAI 服务器登录失败！")
        exit(-1)
    logger.info("OpenAI 服务器登录成功")
    logger.info("尝试从 Mirai 服务中读取机器人 QQ 的 session key……")
    if config.mirai.reverse_ws_port:
        logger.info("[提示] 当前为反向 ws 模式，请确保你的 mirai api http 设置了正确的 reverse-ws adapter 配置")
        logger.info("[提示] 配置不正确会导致 Mirai 端出现错误提示。")

    else:
        logger.info("[提示] 当前为正向 ws + http 模式，请确保你的 mirai api http 设置了正确的 ws 和 http 配置")
        logger.info("[提示] 配置不正确或 Mirai 未登录 QQ 都会导致 【Websocket reconnecting...】 提示的出现。")


cmd = Commander(app.broadcast)


@cmd.command(".重新加载配置文件")
async def update_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if not sender.id == config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        constants.config = config.load_config()
        config.scan_presets()
        await app.send_message(event, "配置文件重新载入完毕！")
        await app.send_message(event, "重新登录账号中，详情请看控制台日志……")
        constants.botManager = BotManager(config)
        await botManager.login()
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
async def show_rate(app: Ariadne, event: MessageEvent, msg_type: str, msg_id: str):
    try:
        if isinstance(event, TempMessage):
            return
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


@cmd.command(".查询API余额")
async def update_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if not sender.id == config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        tasklist = []
        bots = botManager.bots.get("openai-api", [])
        for account in bots:
            tasklist.append(botManager.check_api_info(account))
        msg = await app.send_message(event, "查询中，请稍等……")

        nodes = []
        for account, r in zip(bots, await asyncio.gather(*tasklist)):
            grant_used, grant_available, has_payment_method, total_usage, hard_limit_usd = r
            total_available = grant_available
            if has_payment_method:
                total_available = total_available + hard_limit_usd - total_usage
            answer = '' + account.api_key[:6] + "**" + account.api_key[-3:] + '\n'
            answer = answer + f' - 本月已用: {round(total_usage, 2)}$\n' \
                              f' - 可用：{round(total_available, 2)}$\n' \
                              f' - 绑卡：{has_payment_method}'
            node = ForwardNode(target=config.mirai.qq, message=MessageChain(Plain(answer)))
            nodes.append(node)

        await app.recall_message(msg)
        if len(nodes) == 0:
            await app.send_message(event, "没有查询到任何 API")
            return
        await app.send_message(event, MessageChain(Forward(nodes)))
    finally:
        raise ExecutionStop()

app.launch_blocking()
