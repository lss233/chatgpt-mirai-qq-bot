import time
from typing import Optional

import openai
import telegram.helpers
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger
from telegram import Update, constants, Message
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from telegram.request import HTTPXRequest

from constants import config
from framework.messages import ImageElement
from framework.middlewares.ratelimit import manager as ratelimit_manager
from framework.request import Response, Request
from framework.tts.tts import TTSResponse, VoiceFormat
from framework.universal import handle_message


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    type = 'friend' if update.message.chat.type == constants.ChatType.PRIVATE else 'group' if update.message.chat.type in [
        constants.ChatType.GROUP, constants.ChatType.SUPERGROUP] else None
    if type is None:
        return

    bot_username = (await context.bot.get_me()).username

    if type == 'group' and (bot_username not in update.message.text and (
            update.message.reply_to_message is None or update.message.reply_to_message.from_user is None or update.message.reply_to_message.from_user.username != bot_username)):
        logger.debug(f"忽略消息（未满足匹配规则）: {update.message.text} ")
        return

    last_message_item: Optional[Message] = None
    last_send_text: str = ''

    async def _response_func(chain: MessageChain, text: str, voice: TTSResponse, image: ImageElement):
        nonlocal last_message_item, last_send_text
        if text:
            last_send_text += telegram.helpers.escape_markdown(text, 2)
        if voice:
            await update.message.reply_chat_action(action=telegram.constants.ChatAction.UPLOAD_VOICE)
            last_message_item = await update.message.reply_audio(audio=await voice.transcode(VoiceFormat.Wav),
                                                                 title="Voice Message",
                                                                 caption=last_send_text)
        if image:
            await update.message.reply_chat_action(action=telegram.constants.ChatAction.UPLOAD_PHOTO)
            last_message_item = await update.message.reply_photo(photo=await image.get_bytes(),
                                                                 caption=last_send_text,
                                                                 parse_mode=ParseMode.MARKDOWN_V2)

        elif text:
            await update.message.reply_chat_action(action=telegram.constants.ChatAction.TYPING)
            if last_message_item:
                if last_message_item.text:
                    last_message_item = await last_message_item.edit_text(
                        text=last_send_text,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    last_message_item = await last_message_item.edit_caption(
                        caption=last_send_text,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
            else:
                last_message_item = await update.message.reply_text(
                    text=last_send_text,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        last_send_text = ''

    request = Request()
    request.session_id = f"{type}-{update.message.chat.id}"
    request.user_id = update.message.from_user.id
    request.group_id = update.message.chat_id
    request.nickname = update.message.from_user.full_name or "路人甲"
    request.message = MessageChain(
        [Plain(update.message.text.replace(f"@{bot_username}", '').strip())])

    response = Response(_response_func)

    await update.message.reply_chat_action(action=telegram.constants.ChatAction.TYPING)
    await handle_message(request, response)


async def on_check_presets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
            config.prompts.hide
            and update.message.from_user.id != config.telegram.manager_chat
    ):
        return await update.message.reply_text("您没有权限执行这个操作")
    for keyword, path in config.prompts.keywords.items():
        try:
            with open(path) as f:
                preset_data = f.read().replace("\n\n", "\n=========\n")
            answer = f"预设名：{keyword}\n{preset_data}"
            await update.message.reply_text(answer)
        except BaseException:
            pass


async def on_limit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
            update.message.from_user.id != config.telegram.manager_chat
    ):
        return await update.message.reply_text("您没有权限执行这个操作")
    msg_type, msg_id, rate = update.message.text.split(' ')
    if msg_type not in ["群组", "好友"]:
        return await update.message.reply_text("类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await update.message.reply_text("目标异常，仅支持设定【默认】或【指定 chat id】的额度")
    ratelimit_manager.update(msg_type, msg_id, rate)
    return await update.message.reply_text("额度更新成功！")


async def on_query_chat_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_type, msg_id, rate = update.message.text.split(' ')

    if msg_type not in ["群组", "好友"]:
        return await update.message.reply_text("类型异常，仅支持设定【群组】或【好友】的额度")
    if msg_id != '默认' and not msg_id.isdecimal():
        return await update.message.reply_text("目标异常，仅支持设定【默认】或【指定 chat id】的额度")
    limit = ratelimit_manager.get_limit(msg_type, msg_id)
    if limit is None:
        return await update.message.reply_text(f"{msg_type} {msg_id} 没有额度限制。")
    usage = ratelimit_manager.get_usage(msg_type, msg_id)
    current_time = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(
            time.time()))
    return await update.message.reply_text(
        f"{msg_type} {msg_id} 的额度使用情况：{limit['rate']}条/小时， 当前已发送：{usage['count']}条消息\n整点重置，当前服务器时间：{current_time}")


async def bootstrap() -> None:
    """Set up the application and a custom webserver."""
    app = ApplicationBuilder() \
        .proxy_url(config.telegram.proxy or openai.proxy) \
        .token(config.telegram.bot_token) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .get_updates_request(HTTPXRequest(http_version="1.1")) \
        .http_version('1.1') \
        .build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            on_message))
    app.add_handler(CommandHandler("presets", on_check_presets_list))
    app.add_handler(CommandHandler("limit_chat", on_limit_chat))
    app.add_handler(CommandHandler("query_limit", on_query_chat_limit))
    await app.initialize()
    await app.start()
    logger.info("启动完毕，接收消息中……")
    await app.updater.start_polling(drop_pending_updates=True)


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await bootstrap()
