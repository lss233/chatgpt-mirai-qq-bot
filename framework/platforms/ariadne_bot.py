import datetime
import functools
import time
from typing import Optional, Union

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
from constants import config
from framework.accounts import account_manager
from framework.messages import ImageElement
from framework.middlewares.ratelimit import manager as ratelimit_manager
from framework.request import Request, Response
from framework.tts.tts import TTSResponse
from framework.universal import handle_message
from framework.utils.text_to_img import to_image

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
    app.launch_manager.add_launchable(
        AiohttpServerService(
            config.mirai.reverse_ws_host,
            config.mirai.reverse_ws_port))
else:
    app = Ariadne(
        ariadne_config(
            config.mirai.qq,  # 配置详见
            config.mirai.api_key,
            HttpClientConfig(host=config.mirai.http_url),
            WebsocketClientConfig(host=config.mirai.ws_url),
        ),
    )


async def send_message_with_quote(target: Union[Friend, Group], msg: AriadneBaseModel,
                                  quote: Optional[Source] = None):
    return await app.send_message(
        target,
        msg,
        quote=quote if config.response.quote else False
    )


async def handle_message_failure(target: Union[Friend, Group], msg: MessageChain, quote: Optional[Source] = None):
    logger.warning("原始消息发送失败，尝试通过图片发送")
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
    return await send_message_with_quote(target, MessageChain(rendered_elems), quote)


async def respond(target: Union[Friend, Group], source: Source, msg: AriadneBaseModel):
    # 如果是非字符串
    if not isinstance(msg, Plain) and not isinstance(msg, str):
        event = await send_message_with_quote(target, msg, source)
    # 如果开启了强制转图片
    elif config.text_to_image.always and not isinstance(msg, Voice):
        event = await send_message_with_quote(target, await to_image(str(msg)), source)
    else:
        event = await send_message_with_quote(target, msg, source)

    if event.source.id < 0:
        logger.warning("原始消息发送失败，尝试通过转发发送")
        event = await send_message_with_quote(target, MessageChain(
            Forward(
                [
                    ForwardNode(
                        target=config.mirai.qq,
                        name="ChatGPT",
                        message=msg,
                        time=datetime.datetime.now()
                    )
                ])
        ))

    if event.source.id < 0:
        event = await handle_message_failure(target, msg, source)

    return event


async def response(target: Union[Friend, Group], source: Source, chain: MessageChain = None, text: str = None,
                   voice: TTSResponse = None, image: ImageElement = None):
    try:
        if chain:
            logger.debug(f"[Mirai] 尝试发送消息：{str(chain)}")
            return await respond(target, source, chain)
        elif text:
            return await respond(target, source, MessageChain([Plain(text)]))
        elif voice:
            return await respond(target, source, Voice(voice))
        elif image:
            return await respond(target, source, MessageChain([image]))
        else:
            raise ValueError("没有为response函数提供有效输入")

    except Exception as e:
        logger.error(f"处理响应时发生错误: {e}")


def create_request(
        user_id,
        target_id,
        platform,
        is_manager,
        chain,
        nickname,
        session_prefix):
    request = Request()
    request.user_id = user_id
    request.group_id = target_id
    request.session_id = f"{session_prefix}-{target_id}"
    request.message = chain
    request.platform = platform
    request.is_manager = is_manager
    request.nickname = nickname
    return request


FriendTrigger = DetectPrefix(
    config.trigger.prefix +
    config.trigger.prefix_friend)


@app.broadcast.receiver("FriendMessage", priority=19)
async def friend_message_listener(app: Ariadne, target: Friend, source: Source,
                                  chain: MessageChain):
    try:
        chain = await FriendTrigger(chain, None)
    except BaseException:
        logger.debug(f"丢弃私聊消息：{chain.display}（原因：不符合触发前缀）")
        return

    if target.id == config.mirai.qq:
        return
    if chain.display.startswith("."):
        return

    request = create_request(
        target.id,
        target.id,
        constants.BotPlatform.AriadneBot,
        target.id == config.mirai.manager_qq,
        chain,
        target.nickname,
        "friend")

    respond_partial = functools.partial(response, target, source)
    response_obj = Response(respond_partial)

    try:
        await handle_message(request, response_obj)
    except Exception as e:
        logger.exception(e)


GroupTrigger = Annotated[MessageChain, MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix + config.trigger.prefix_group)] if config.trigger.require_mention != "none" else Annotated[
    MessageChain, DetectPrefix(config.trigger.prefix)]


@app.broadcast.receiver("GroupMessage", priority=19)
async def group_message_listener(target: Group, source: Source, chain: GroupTrigger, member: Member):
    if chain.display.startswith("."):
        return

    request = create_request(
        member.id,
        target.id,
        constants.BotPlatform.AriadneBot,
        member.id == config.mirai.manager_qq,
        chain,
        member.name,
        "group")

    respond_partial = functools.partial(response, target, source)
    response_obj = Response(respond_partial)

    try:
        await handle_message(request, response_obj)
    except Exception as e:
        logger.exception(e)


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
        logger.info(
            "[提示] 当前为反向 ws 模式，请确保你的 mirai api http 设置了正确的 reverse-ws adapter 配置")
        logger.info("[提示] 配置不正确会导致 Mirai 端出现错误提示。")

    else:
        logger.info(
            "[提示] 当前为正向 ws + http 模式，请确保你的 mirai api http 设置了正确的 ws 和 http 配置")
        logger.info(
            "[提示] 配置不正确或 Mirai 未登录 QQ 都会导致 【Websocket reconnecting...】 提示的出现。")


cmd = Commander(app.broadcast)


@cmd.command(".重新加载配置文件")
async def configuration_reload(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if sender.id != config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        constants.config = config.load_config()
        config.scan_prompts()
        await app.send_message(event, "配置文件重新载入完毕！")
        await app.send_message(event, "重新登录账号中，详情请看控制台日志……")
        await account_manager.load_accounts(constants.config.accounts)
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
        current_time = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(
                time.time()))
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
        current_time = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(
                time.time()))
        return await app.send_message(event,
                                      f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")
    finally:
        raise ExecutionStop()


@cmd.command(".预设列表")
async def presets_list(app: Ariadne, event: MessageEvent, sender: Union[Friend, Member]):
    try:
        if config.prompts.hide and sender.id != config.mirai.manager_qq:
            return await app.send_message(event, "您没有权限执行这个操作")
        nodes = []
        for keyword, path in config.prompts.keywords.items():
            try:
                with open(path, 'rb') as f:
                    guessed_str = from_bytes(f.read()).best()
                    preset_data = str(guessed_str).replace(
                        "\n\n", "\n=========\n")
                answer = f"预设名：{keyword}\n{preset_data}"

                node = ForwardNode(
                    target=config.mirai.qq,
                    name="ChatGPT",
                    message=MessageChain(Plain(answer)),
                    time=datetime.datetime.now()
                )
                nodes.append(node)
            except BaseException:
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
