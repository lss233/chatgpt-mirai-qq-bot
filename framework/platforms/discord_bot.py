import os
import sys
from io import BytesIO
from typing import Optional

import discord
from discord import Message
from discord.ext import commands
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain

from framework.messages import ImageElement
from framework.request import Request, Response
from framework.tts.tts import TTSResponse, VoiceFormat
from framework.universal import handle_message

sys.path.append(os.getcwd())

from constants import config

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents, proxy=config.discord.proxy)


async def on_message_event(message: discord.Message) -> None:
    if message.author == bot.user:
        return
    bot_id = f"{bot.user.id}".split("#")[0]

    # Check if the message is a reply to the bot
    is_reply_to_bot = False
    if message.reference:
        try:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author == bot.user:
                is_reply_to_bot = True
        except discord.NotFound:
            pass

    if not is_reply_to_bot and not message.content.startswith(f"<@{bot_id}>"):
        return

    last_message_item: Optional[Message] = None
    last_send_text: str = ''

    async def _response_func(chain: MessageChain, text: str, voice: TTSResponse, image: ImageElement):
        nonlocal last_message_item, last_send_text
        if text:
            last_send_text += text
        if voice:
            last_message_item = await message.reply(file=discord.File(BytesIO(await voice.transcode(VoiceFormat.Wav)),
                                                  filename="voice.wav"),
                                content=last_send_text)
        if image:
            last_message_item = await message.reply(file=discord.File(BytesIO(await image.get_bytes()),
                                                  filename="image.png"),
                                content=last_send_text)

        elif text:
            if last_message_item:
                last_message_item = await last_message_item.edit(content=last_send_text)
            else:
                last_message_item = await message.reply(content=last_send_text)
        last_send_text = ''

    request = Request()
    request.session_id = f"{'friend' if isinstance(message.channel, discord.DMChannel) else 'group'}-{message.channel.id}"
    request.user_id = message.author.id
    request.group_id = message.channel.id
    request.nickname = message.author.name
    request.message = MessageChain([Plain(message.content.replace(f"<@{bot_id}>", "").strip())])

    response = Response(_response_func)

    await handle_message(request, response)

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    await on_message_event(message)


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await bot.start(config.discord.bot_token)
