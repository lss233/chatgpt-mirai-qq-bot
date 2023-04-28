import os
import sys
from io import BytesIO

import discord
from discord.ext import commands
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain, Voice

from universal import handle_message

sys.path.append(os.getcwd())

from constants import config, BotPlatform

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)


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

    async def response(msg):
        if isinstance(msg, MessageChain):
            for elem in msg:
                if isinstance(elem, Plain) and str(elem):
                    chunks = [str(elem)[i:i + 1500] for i in range(0, len(str(elem)), 1500)]
                    for chunk in chunks:
                        await message.reply(chunk)
                if isinstance(elem, Image):
                    await message.reply(file=discord.File(BytesIO(await elem.get_bytes()), filename='image.png'))
                if isinstance(elem, Voice):
                    await message.reply(file=discord.File(BytesIO(await elem.get_bytes()), filename="voice.wav"))
            return
        if isinstance(msg, str):
            chunks = [str(msg)[i:i + 1500] for i in range(0, len(str(msg)), 1500)]
            for chunk in chunks:
                await message.reply(chunk)
            return
        if isinstance(msg, Image):
            return await message.reply(file=discord.File(BytesIO(await msg.get_bytes()), filename='image.png'))
        if isinstance(msg, Voice):
            await message.reply(file=discord.File(BytesIO(await msg.get_bytes()), filename="voice.wav"))
            return

    await handle_message(response,
                         f"{'friend' if isinstance(message.channel, discord.DMChannel) else 'group'}-{message.channel.id}",
                         message.content.replace(f"<@{bot_id}>", "").strip(), is_manager=False,
                         nickname=message.author.name, request_from=BotPlatform.DiscordBot)

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    await on_message_event(message)


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await bot.start(config.discord.bot_token)
