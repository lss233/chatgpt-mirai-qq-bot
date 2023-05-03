import time
import openai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain, Voice
from loguru import logger
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from telegram.request import HTTPXRequest
from framework.middlewares.ratelimit import manager as ratelimit_manager

from constants import config, BotPlatform
from universal import handle_message


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    type = 'friend' if update.message.chat.type == constants.ChatType.PRIVATE else 'group' if update.message.chat.type in [
        constants.ChatType.GROUP, constants.ChatType.SUPERGROUP] else None
    if type is None:
        return

    bot_username = (await context.bot.get_me()).username

    if type == 'group' and (
            bot_username not in update.message.text and (
            update.message.reply_to_message is None or update.message.reply_to_message.from_user is None or update.message.reply_to_message.from_user.username != bot_username)
    ):
        logger.debug(f"忽略消息（未满足匹配规则）: {update.message.text} ")
        return

    async def response(msg):
        if isinstance(msg, MessageChain):
            for elem in msg:
                if isinstance(elem, Plain):
                    await update.message.reply_text(str(elem))
                if isinstance(elem, Image):
                    await update.message.reply_photo(photo=await elem.get_bytes())
                if isinstance(elem, Voice):
                    await update.message.reply_audio(audio=await elem.get_bytes())
            return
        if isinstance(msg, str):
            return await update.message.reply_text(msg)
        if isinstance(msg, Image):
            return await update.message.reply_photo(photo=await msg.get_bytes())
        if isinstance(msg, Voice):
            await update.message.reply_audio(audio=await msg.get_bytes(), title="Voice")
            return

    await handle_message(
        response,
        f"{type}-{update.message.chat.id}",
        update.message.text.replace(f"@{bot_username}", '').strip(),
        is_manager=update.message.from_user.id == config.telegram.manager_chat,
        nickname=update.message.from_user.full_name or "群友",
        request_from=BotPlatform.TelegramBot
    )


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
        except:
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
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
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

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
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
