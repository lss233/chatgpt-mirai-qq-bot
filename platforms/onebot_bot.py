import re
import time
from base64 import b64decode, b64encode
from typing import Union, Optional

import aiohttp
from aiocqhttp import CQHttp, Event, MessageSegment
from charset_normalizer import from_bytes
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image as GraiaImage, At, Plain, Voice
from graia.ariadne.message.parser.base import DetectPrefix
from graia.broadcast import ExecutionStop
from loguru import logger

import constants
from constants import config, botManager
from manager.bot import BotManager
from middlewares.ratelimit import manager as ratelimit_manager
from universal import handle_message

bot = CQHttp()


class MentionMe:
    """At 账号或者提到账号群昵称"""

    def __init__(self, name: Union[bool, str] = True) -> None:
        self.name = name

    async def __call__(self, chain: MessageChain, event: Event) -> Optional[MessageChain]:
        first = chain[0]
        if isinstance(first, At) and first.target == event.self_id:
            return MessageChain(chain.__root__[1:], inline=True).removeprefix(" ")
        elif isinstance(first, Plain):
            member_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)
            if member_info.get("nickname") and chain.startswith(member_info.get("nickname")):
                return chain.removeprefix(" ")
        raise ExecutionStop


class Image(GraiaImage):
    async def get_bytes(self) -> bytes:
        """尝试获取消息元素的 bytes, 注意, 你无法获取并不包含 url 且不包含 base64 属性的本元素的 bytes.

        Raises:
            ValueError: 你尝试获取并不包含 url 属性的本元素的 bytes.

        Returns:
            bytes: 元素原始数据
        """
        if self.base64:
            return b64decode(self.base64)
        if not self.url:
            raise ValueError("you should offer a url.")
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                data = await response.read()
                self.base64 = b64encode(data).decode("ascii")
                return data


# TODO: use MessageSegment
# https://github.com/nonebot/aiocqhttp/blob/master/docs/common-topics.md
def transform_message_chain(text: str) -> MessageChain:
    pattern = r"\[CQ:(\w+),([^\]]+)\]"
    matches = re.finditer(pattern, text)

    message_classes = {
        "text": Plain,
        "image": Image,
        "at": At,
        # Add more message classes here
    }

    messages = []
    start = 0
    for match in matches:
        cq_type, params_str = match.groups()
        params = dict(re.findall(r"(\w+)=([^,]+)", params_str))
        if message_class := message_classes.get(cq_type):
            text_segment = text[start:match.start()]
            if text_segment and not text_segment.startswith('[CQ:reply,'):
                messages.append(Plain(text_segment))
            if cq_type == "at":
                if params.get('qq') == 'all':
                    continue
                params["target"] = int(params.pop("qq"))
            elem = message_class(**params)
            messages.append(elem)
            start = match.end()
    if text_segment := text[start:]:
        messages.append(Plain(text_segment))

    return MessageChain(*messages)


def transform_from_message_chain(chain: MessageChain):
    result = ''
    for elem in chain:
        if isinstance(elem, (Image, GraiaImage)):
            result = result + MessageSegment.image(f"base64://{elem.base64}")
        elif isinstance(elem, Plain):
            result = result + MessageSegment.text(str(elem))
        elif isinstance(elem, Voice):
            result = result + MessageSegment.record(f"base64://{elem.base64}")
    return result


def response(event, is_group: bool):
    async def respond(resp):
        logger.debug(f"[OneBot] 尝试发送消息：{str(resp)}")
        try:
            if not isinstance(resp, MessageChain):
                resp = MessageChain(resp)
            resp = transform_from_message_chain(resp)
            if config.response.quote and '[CQ:record,file=' not in str(resp):  # skip voice
                resp = MessageSegment.reply(event.message_id) + resp
            return await bot.send(event, resp)
        except Exception as e:
            logger.exception(e)
            logger.warning("原始消息发送失败，尝试通过转发发送")
            return await bot.call_action(
                "send_group_forward_msg" if is_group else "send_private_forward_msg",
                group_id=event.group_id,
                messages=[
                    MessageSegment.node_custom(event.self_id, "ChatGPT", resp)
                ]
            )

    return respond


FriendTrigger = DetectPrefix(config.trigger.prefix + config.trigger.prefix_friend)


@bot.on_message('private')
async def _(event: Event):
    if event.message.startswith('.'):
        return
    chain = transform_message_chain(event.message)
    try:
        msg = await FriendTrigger(chain, None)
    except:
        logger.debug(f"丢弃私聊消息：{event.message}（原因：不符合触发前缀）")
        return

    logger.debug(f"私聊消息：{event.message}")

    try:
        await handle_message(
            response(event, False),
            f"friend-{event.user_id}",
            msg.display,
            chain,
            is_manager=event.user_id == config.onebot.manager_qq,
            nickname=event.sender.get("nickname", "好友"),
            request_from=constants.BotPlatform.Onebot
        )
    except Exception as e:
        logger.exception(e)


GroupTrigger = [MentionMe(config.trigger.require_mention != "at"), DetectPrefix(
    config.trigger.prefix + config.trigger.prefix_group)] if config.trigger.require_mention != "none" else [
    DetectPrefix(config.trigger.prefix)]


@bot.on_message('group')
async def _(event: Event):
    if event.message.startswith('.'):
        return
    chain = transform_message_chain(event.message)
    try:
        for it in GroupTrigger:
            chain = await it(chain, event)
    except:
        logger.debug(f"丢弃群聊消息：{event.message}（原因：不符合触发前缀）")
        return

    logger.debug(f"群聊消息：{event.message}")

    await handle_message(
        response(event, True),
        f"group-{event.group_id}",
        chain.display,
        is_manager=event.user_id == config.onebot.manager_qq,
        nickname=event.sender.get("nickname", "群友"),
        request_from=constants.BotPlatform.Onebot
    )


@bot.on_message()
async def _(event: Event):
    if event.message != ".重新加载配置文件":
        return
    if event.user_id != config.onebot.manager_qq:
        return await bot.send(event, "您没有权限执行这个操作")
    constants.config = config.load_config()
    config.scan_presets()
    await bot.send(event, "配置文件重新载入完毕！")
    await bot.send(event, "重新登录账号中，详情请看控制台日志……")
    constants.botManager = BotManager(config)
    await botManager.login()
    await bot.send(event, "登录结束")


@bot.on_message()
async def _(event: Event):
    pattern = r"\.设置\s+(\w+)\s+(\S+)\s+额度为\s+(\d+)\s+条/小时"
    match = re.match(pattern, event.message.strip())
    if not match:
        return
    if event.user_id != config.onebot.manager_qq:
        return await bot.send(event, "您没有权限执行这个操作")
    msg_type, msg_id, rate = match.groups()
    rate = int(rate)

    if msg_type not in ["群组", "好友"]:
        return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
    ratelimit_manager.update(msg_type, msg_id, rate)
    return await bot.send(event, "额度更新成功！")


@bot.on_message()
async def _(event: Event):
    pattern = r"\.设置\s+(\w+)\s+(\S+)\s+画图额度为\s+(\d+)\s+个/小时"
    match = re.match(pattern, event.message.strip())
    if not match:
        return
    if event.user_id != config.onebot.manager_qq:
        return await bot.send(event, "您没有权限执行这个操作")
    msg_type, msg_id, rate = match.groups()
    rate = int(rate)

    if msg_type not in ["群组", "好友"]:
        return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
    ratelimit_manager.update_draw(msg_type, msg_id, rate)
    return await bot.send(event, "额度更新成功！")


@bot.on_message()
async def _(event: Event):
    pattern = r"\.查看\s+(\w+)\s+(\S+)\s+的使用情况"
    match = re.match(pattern, event.message.strip())
    if not match:
        return

    msg_type, msg_id = match.groups()

    if msg_type not in ["群组", "好友"]:
        return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
    limit = ratelimit_manager.get_limit(msg_type, msg_id)
    if limit is None:
        return await bot.send(event, f"{msg_type} {msg_id} 没有额度限制。")
    usage = ratelimit_manager.get_usage(msg_type, msg_id)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    return await bot.send(event,
                          f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")


@bot.on_message()
async def _(event: Event):
    pattern = r"\.查看\s+(\w+)\s+(\S+)\s+的画图使用情况"
    match = re.match(pattern, event.message.strip())
    if not match:
        return

    msg_type, msg_id = match.groups()

    if msg_type not in ["群组", "好友"]:
        return await bot.send(event, "类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await bot.send(event, "目标异常，仅支持设定【默认】或【指定 QQ（群）号】的额度")
    limit = ratelimit_manager.get_draw_limit(msg_type, msg_id)
    if limit is None:
        return await bot.send(event, f"{msg_type} {msg_id} 没有额度限制。")
    usage = ratelimit_manager.get_draw_usage(msg_type, msg_id)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    return await bot.send(event,
                          f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}个图/小时， 当前已绘制：{usage['count']}个图\n整点重置，当前服务器时间：{current_time}")


@bot.on_message()
async def _(event: Event):
    pattern = ".预设列表"
    event.message = str(event.message)
    if event.message.strip() != pattern:
        return

    if config.presets.hide and event.user_id != config.onebot.manager_qq:
        return await bot.send(event, "您没有权限执行这个操作")
    nodes = []
    for keyword, path in config.presets.keywords.items():
        try:
            with open(path, 'rb') as f:
                guessed_str = from_bytes(f.read()).best()
                preset_data = str(guessed_str).replace("\n\n", "\n=========\n")
            answer = f"预设名：{keyword}\n{preset_data}"

            node = MessageSegment.node_custom(event.self_id, "ChatGPT", answer)
            nodes.append(node)
        except Exception as e:
            logger.error(e)

    if not nodes:
        await bot.send(event, "没有查询到任何预设！")
        return
    try:
        if event.group_id:
            await bot.call_action("send_group_forward_msg", group_id=event.group_id, messages=nodes)
        else:
            await bot.call_action("send_private_forward_msg", user_id=event.user_id, messages=nodes)
    except Exception as e:
        logger.exception(e)
        await bot.send(event, "消息发送失败！请在私聊中查看。")


@bot.on_request
async def _(event: Event):
    if config.system.accept_friend_request:
        await bot.call_action(
            action='.handle_quick_operation_async',
            self_id=event.self_id,
            context=event,
            operation={'approve': True}
        )


@bot.on_request
async def _(event: Event):
    if config.system.accept_group_invite:
        await bot.call_action(
            action='.handle_quick_operation_async',
            self_id=event.self_id,
            context=event,
            operation={'approve': True}
        )


@bot.on_startup
async def startup():
    logger.success("启动完毕，接收消息中……")


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await bot.run_task(host=config.onebot.reverse_ws_host, port=config.onebot.reverse_ws_port)
