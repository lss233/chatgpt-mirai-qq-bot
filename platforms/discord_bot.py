import os
import sys

import datetime
import discord
from discord.ext import commands

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from universal import handle_message
from io import BytesIO
import azure.cognitiveservices.speech as speechsdk

sys.path.append(os.getcwd())

from constants import config, botManager

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

# 这个函数放在这里, lss233 肯定会骂我的 (by copilot)
def synthesize_speech(text: str, output_file: str, voice: str = "en-SG-WayneNeural"): # Singapore English, Wayne
    account = config.azure.tts_accounts[0] if config.azure else []
    if account.speech_key:
        speech_key, service_region = account.speech_key, account.speech_service_region
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        # https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/text-to-speech
        speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_SynthVoice, voice)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_text_async(text).get()
    else:
        return False

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    else:
        return False

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
                        ts = datetime.datetime.now().timestamp()
                        if synthesize_speech(chunk, f"output-{ ts }.wav"):
                            await message.reply(file=discord.File(f"output-{ ts }.wav", filename="voice.wav"))
                    return
                elif isinstance(elem, Image):
                    return await message.reply(file=discord.File(BytesIO(await elem.get_bytes()), filename='image.png'))
        if isinstance(msg, str):
            chunks = [str(msg)[i:i + 1500] for i in range(0, len(str(msg)), 1500)]
            for chunk in chunks:
                await message.reply(chunk)
                ts = datetime.datetime.now().timestamp()
                if synthesize_speech(chunk, f"output-{ ts }.wav"):
                    await message.reply(file=discord.File(f"output-{ ts }.wav", filename="voice.wav"))
            return
        elif isinstance(msg, Image):
            return await message.reply(file=discord.File(BytesIO(await msg.get_bytes()), filename='image.png'))

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
