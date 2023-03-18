import os
import sys

import openai
from graia.ariadne.message.element import Image
from loguru import logger

from universal import handle_message

sys.path.append(os.getcwd())

from constants import botManager, config

from telegram import Update, constants, error
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler, CallbackContext, Defaults

botManager.login()

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    type = 'friend' if update.message.chat.type == constants.ChatType.PRIVATE else 'group' if update.message.chat.type in [
        constants.ChatType.GROUP, constants.ChatType.SUPERGROUP] else None
    if type is None:
        return
    
    bot_username = (await context.bot.get_me()).username
    if not bot_username in update.message.text and (update.message.reply_to_message is None or update.message.reply_to_message.from_user is None or update.message.reply_to_message.from_user.username != bot_username):
        return

    async def response(msg):
        if isinstance(msg, str):
            return await update.message.reply_text(msg)
        elif isinstance(msg, Image):
            return await update.message.reply_photo(photo=await msg.get_bytes())

    await handle_message(response, f"{type}-{update.message.chat.id}", update.message.text.replace(f"@{bot_username}", '').strip())

def error_handler(update: Update, context: CallbackContext) -> None:
    if isinstance(context.error, error.TelegramError) and not context.error.should_retry():
        try:
            context.dispatcher.bot.start_polling()
        except Exception as e:
            pass

app = ApplicationBuilder()\
    .proxy_url(config.telegram.proxy or openai.proxy)\
    .token(config.telegram.bot_token)\
    .build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
app.add_error_handler(error_handler)
logger.info("启动完毕，接收消息中……")
app.run_polling()
