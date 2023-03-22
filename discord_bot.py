import os
import sys
import discord
from discord.ext import commands

import openai
from graia.ariadne.message.element import Image
from loguru import logger

from universal import handle_message

sys.path.append(os.getcwd())

from constants import botManager, config

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)
botManager.login()

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
        if isinstance(msg, str):
            await message.channel.send(msg)
        elif isinstance(msg, Image):
            file = discord.File(await msg.get_bytes(), filename='image.png')
            await message.channel.send(file=file)

    await handle_message(response, f"{'friend' if isinstance(message.channel, discord.DMChannel) else 'group'}-{message.channel.id}", message.content.replace(f"<@{bot_id}>", "").strip(), is_manager=False)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready. Logged in as {bot.user.name}-{bot.user.id}")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    await on_message_event(message)

bot.run(config.discord.bot_token)