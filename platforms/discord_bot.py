import os
import sys

import asyncio
import discord
from discord.ext import commands

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from universal import handle_message

sys.path.append(os.getcwd())

from constants import config, botManager

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
                        await message.channel.send(chunk)
                    return
                elif isinstance(elem, Image) and elem.get_bytes():
                    return await message.channel.send(file=discord.File(elem.get_bytes()))
        if isinstance(msg, str):
            chunks = [str(msg)[i:i + 1500] for i in range(0, len(str(msg)), 1500)]
            for chunk in chunks:
                await message.channel.send(chunk)
            return
        elif isinstance(msg, Image):
            file = discord.File(await msg.get_bytes(), filename='image.png')
            return await message.channel.send(file=file)

    await handle_message(response,
                         f"{'friend' if isinstance(message.channel, discord.DMChannel) else 'group'}-{message.channel.id}",
                         message.content.replace(f"<@{bot_id}>", "").strip(), is_manager=False,
                         nickname=message.author.name)


@bot.event
async def on_ready():
    await botManager.login()
    logger.info(f"Bot is ready. Logged in as {bot.user.name}-{bot.user.id}")


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    await on_message_event(message)


def main():
    bot.run(config.discord.bot_token)
