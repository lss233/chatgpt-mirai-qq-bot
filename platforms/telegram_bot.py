import math
import os
import sys

import asyncio
import openai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain, Voice
from loguru import logger
from telegram.request import HTTPXRequest
from io import BytesIO, IOBase
from universal import handle_message

sys.path.append(os.getcwd())

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
            await update.message.reply_audio(audio=await msg.get_bytes())
            return

    await handle_message(
        response,
        f"{type}-{update.message.chat.id}",
        update.message.text.replace(f"@{bot_username}", '').strip(),
        is_manager=update.message.from_user.id == config.telegram.manager_chat,
        nickname=update.message.from_user.full_name or "群友"
    )


async def on_check_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.from_user.id == config.telegram.manager_chat:
        return await update.message.reply_text("您没有权限执行这个操作")

    tasklist = []
    bots = botManager.bots.get("openai-api", [])
    for account in bots:
        tasklist.append(botManager.check_api_info(account))
    msg = await update.message.reply_text("查询中，请稍等……")
    answer = ''
    for account, r in zip(bots, await asyncio.gather(*tasklist)):
        grant_used, grant_available, has_payment_method, total_usage, hard_limit_usd = r
        total_available = grant_available
        if has_payment_method:
            total_available = total_available + hard_limit_usd - total_usage
        answer = answer + '* `' + account.api_key[:6] + "**" + account.api_key[-3:] + '`'
        answer = answer + f' - ' + f'本月已用: `{round(total_usage, 2)}$`, 可用：`{round(total_available, 2)}$`, 绑卡：{has_payment_method}'
        answer = answer + '\n'
    if answer == '':
        await msg.edit_text("没有查询到任何 API")
        return
    await msg.edit_text(answer)


async def bootstrap() -> None:
    """Set up the application and a custom webserver."""
    app = ApplicationBuilder() \
        .proxy_url(config.telegram.proxy or openai.proxy) \
        .token(config.telegram.bot_token) \
        .connect_timeout(30)\
        .read_timeout(30)\
        .write_timeout(30)\
        .get_updates_request(HTTPXRequest(http_version="1.1")) \
        .http_version('1.1') \
        .build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(CommandHandler("check_api", on_check_api))
    await app.initialize()
    await botManager.login()
    await app.start()
    logger.info("启动完毕，接收消息中……")
    await app.updater.start_polling(drop_pending_updates=True)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bootstrap())
    loop.run_forever()
