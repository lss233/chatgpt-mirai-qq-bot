import os
import sys

import openai
from graia.ariadne.message.element import Image
from loguru import logger
from telegram.request import HTTPXRequest

from universal import handle_message

sys.path.append(os.getcwd())

from constants import botManager, config

from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

botManager.login()


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    type = 'friend' if update.message.chat.type == constants.ChatType.PRIVATE else 'group' if update.message.chat.type in [
        constants.ChatType.GROUP, constants.ChatType.SUPERGROUP] else None
    if type is None:
        return

    async def response(msg):
        if isinstance(msg, str):
            return await update.message.reply_text(msg)
        elif isinstance(msg, Image):
            return await update.message.reply_photo(photo=await msg.get_bytes())

    await handle_message(response, f"{type}-{update.message.chat.id}", update.message.text)


app = ApplicationBuilder()\
    .proxy_url(config.telegram.proxy or openai.proxy)\
    .token(config.telegram.bot_token)\
    .get_updates_request(HTTPXRequest(http_version="1.1")) \
    .http_version('1.1') \
    .build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
logger.info("启动完毕，接收消息中……")
app.run_polling()
