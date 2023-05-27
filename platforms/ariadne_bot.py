import datetime
import time
from typing import Union

from charset_normalizer import from_bytes
from graia.amnesia.builtins.aiohttp import AiohttpServerService
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import (
    HttpClientConfig,
    WebsocketClientConfig,
    config as ariadne_config, WebsocketServerConfig,
)
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.ariadne.event.message import MessageEvent, TempMessage
from graia.ariadne.event.mirai import NewFriendRequestEvent, BotInvitedJoinGroupRequestEvent
from graia.ariadne.message import Source
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.commander import Commander
from graia.ariadne.message.element import ForwardNode, Plain, Forward, Voice
from graia.ariadne.message.parser.base import DetectPrefix, MentionMe
from graia.ariadne.model import Friend, Group, Member, AriadneBaseModel
from graia.broadcast.exceptions import ExecutionStop
from loguru import logger
from typing_extensions import Annotated

import constants
from constants import config, botManager
from manager.bot import BotManager
from middlewares.ratelimit import manager as ratelimit_manager
from universal import handle_message
from utils.text_to_img import to_image

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
    return


async def response_as_text(target: Union[Friend, Group], source: Source, response):
    return await app.send_message(target, response, quote=source if config.response.quote else False)


def response(target: Union[Friend, Group], source: Source):
    async def respond(msg: AriadneBaseModel):
        # 如果是非字符串
        if not isinstance(msg, Plain) and not isinstance(msg, str):
            event = await app.send_message(
                target,
                msg,
                quote=source if config.response.quote else False
            )
        # 如果开启了强制转图片
        elif config.text_to_image.always and not isinstance(msg, Voice):
            event = await app.send_message(
                target,
                await to_image(str(msg)),
                quote=source if config.response.quote else False
            )
        else:
            event = await app.send_message(
                target,
                msg,
                quote=source if config.response.quote else False
            )
        if event.source.id < 0:
            event = await app.send_message(
                target,
                MessageChain(
                    Forward(
                        [
                            ForwardNode(
                                target=config.mirai.qq,
                                name="ChatGPT",
                                message=msg,
                                time=datetime.datetime.now()
                            )
                        ]
                    )
                )
            )
        if event.source.id < 0:
            await app.send_message(
                target,
                "消息发送失败，被TX吞了，尝试转成图片再试一次，请稍等",
                quote=source if config.response.quote else False
            )
            new_elems = []
            for elem in msg:
                if not new_elems:
                    new_elems.append(elem)
                elif isinstance(new_elems[-1], Plain) and isinstance(elem, Plain):
                    new_elems[-1].text = new_elems[-1].text + '\n' + elem.text
                else:
                    new_elems.append(elem)
            rendered_elems = []
            for elem in new_elems:
                if isinstance(elem, Plain):
                    rendered_elems.append(await to_image(elem))
                else:
                    rendered_elems.append(elem)
            event = await app.send_message(
                target,
                MessageChain(rendered_elems),
                quote=source if config.response.quote else False
            )
        return event

    return respond


FriendTrigger = DetectPrefix(config.trigger.prefix + config.trigger.prefix_friend)


@app.broadcast.receiver("FriendMessage", priority=19)
async def friend_message_listener(app: Ariadne, target: Friend, source: Source,
                                  chain: MessageChain):
    try:
        chain = await FriendTrigger(chain, None)
    except:
        logger.debug(f"丢弃私聊消息：{chain.display}（原因：不符合触发前缀）")
        return

    if target.id == config.mirai.qq:
        return
    if chain.display.startswith("."):
        return

    await handle_message(
        response(target, source),
        f"friend-{target.id}",
        chain.display,
        chain,
        is_manager=target.id == config.mirai.manager_qq,
        nickname=target.nickname
    )


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix + config.trigger.prefix_group)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage", priority=19)
async def group_message_listener(target: Group, source: Source, chain: GroupTrigger, member: Member):
    if chain.display.startswith("."):
        return

    await handle_message(
        response(target, source),
        f"group-{target.id}",
        chain.display,
        chain,
        is_manager=member.id == config.mirai.manager_qq,
        nickname=member.name
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
        if sender.id != config.mirai.manager_qq:
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
        if sender.id != config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        if msg_type not in ["群组", "好友"]:
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        ratelimit_manager.update(msg_type, msg_id, rate)
        return await app.send_message(event, "额度更新成功！")
    finally:
        raise ExecutionStop()


@cmd.command(".设置 {msg_type: str} {msg_id: str} 画图额度为 {rate: int} 个/小时")
async def update_rate(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member], msg_type: str, msg_id: str,
                      rate: int):
    try:
        if sender.id != config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        if msg_type not in ["群组", "好友"]:
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        ratelimit_manager.update_draw(msg_type, msg_id, rate)
        return await app.send_message(event, "额度更新成功！")
    finally:
        raise ExecutionStop()



@cmd.command(".查看 {msg_type: str} {msg_id: str} 的使用情况")
async def show_rate(app: Ariadne, event: MessageEvent, msg_type: str, msg_id: str):
    try:
        if isinstance(event, TempMessage):
            return
        if msg_type not in ["群组", "好友"]:
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


@cmd.command(".查看 {msg_type: str} {msg_id: str} 的画图使用情况")
async def show_rate(app: Ariadne, event: MessageEvent, msg_type: str, msg_id: str):
    try:
        if isinstance(event, TempMessage):
            return
        if msg_type not in ["群组", "好友"]:
            return await app.send_message(event, "类型异常，仅支持设定【群组】或【好友】的额度")
        if msg_id != '默认' and not msg_id.isdecimal():
            return await app.send_message(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
        limit = ratelimit_manager.get_draw_limit(msg_type, msg_id)
        if limit is None:
            return await app.send_message(event, f"{msg_type} {msg_id} 没有额度限制。")
        usage = ratelimit_manager.get_draw_usage(msg_type, msg_id)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        return await app.send_message(event,
                                      f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")
    finally:
        raise ExecutionStop()



@cmd.command(".预设列表")
async def presets_list(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if config.presets.hide and sender.id != config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        nodes = []
        for keyword, path in config.presets.keywords.items():
            try:
                with open(path, 'rb') as f:
                    guessed_str = from_bytes(f.read()).best()
                    preset_data = str(guessed_str).replace("\n\n", "\n=========\n")
                answer = f"预设名：{keyword}\n{preset_data}"

                node = ForwardNode(
                    target=config.mirai.qq,
                    name="ChatGPT",
                    message=MessageChain(Plain(answer)),
                    time=datetime.datetime.now()
                )
                nodes.append(node)
            except:
                pass

        if not nodes:
            await app.send_message(event, "没有查询到任何预设")
            return
        await app.send_message(event, MessageChain(Forward(nodes)))
    except Exception as e:
        logger.exception(e)
        await app.send_message(event, MessageChain("消息发送失败！请在私聊中查看。"))
    finally:
        raise ExecutionStop()


async def start_task():
    """|coro|
    以异步方式启动
    """
    app._patch_launch_manager()
    await app.launch_manager.launch()
