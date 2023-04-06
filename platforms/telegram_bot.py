import asyncio
import openai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain, Voice
from loguru import logger
from telegram.request import HTTPXRequest

from universal import handle_message

from constants import botManager, config

from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler


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
        nickname=update.message.from_user.full_name or "群友"
    )

async def on_check_presets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.presets.hide and not update.message.from_user.id == config.telegram.manager_chat:
        return await update.message.reply_text("您没有权限执行这个操作")
    for keyword, path in config.presets.keywords.items():
        try:
            with open(path) as f:
                preset_data = f.read().replace("\n\n", "\n=========\n")
            answer = f"预设名：{keyword}\n" + preset_data
            await update.message.reply_text(answer)
        except:
            pass


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
    await app.initialize()
    await app.start()
    logger.info("启动完毕，接收消息中……")
    await app.updater.start_polling(drop_pending_updates=True)


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await bootstrap()
