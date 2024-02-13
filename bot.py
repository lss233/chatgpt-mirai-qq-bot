import os
import sys
import creart
sys.path.append(os.getcwd())
from asyncio import AbstractEventLoop
import asyncio
from utils.exithooks import hook
from loguru import logger
from constants import config, botManager
from utils.edge_tts import load_edge_tts_voices

loop = creart.create(AbstractEventLoop)

loop.run_until_complete(botManager.login())

bots = []

# 将log输出到stdout
logger.configure(handlers=[{"sink": sys.stdout}])

if config.mirai:
    logger.info("检测到 mirai 配置，将启动 mirai 模式……")
    from platforms.ariadne_bot import start_task

    bots.append(loop.create_task(start_task()))

if config.onebot:
    logger.info("检测到 Onebot 配置，将启动 Onebot 模式……")
    from platforms.onebot_bot import start_task

    bots.append(loop.create_task(start_task()))
if config.telegram:
    logger.info("检测到 telegram 配置，将启动 telegram bot 模式……")
    from platforms.telegram_bot import start_task

    bots.append(loop.create_task(start_task()))
if config.discord:
    logger.info("检测到 discord 配置，将启动 discord bot 模式……")
    from platforms.discord_bot import start_task

    bots.append(loop.create_task(start_task()))
if config.http:
    logger.info("检测到 http 配置，将启动 http service 模式……")
    from platforms.http_service import start_task

    bots.append(loop.create_task(start_task()))
if config.wecom:
    logger.info("检测到 Wecom 配置，将启动 Wecom Bot 模式……")
    from platforms.wecom_bot import start_task

    bots.append(loop.create_task(start_task()))
try:
    logger.info("[Edge TTS] 读取 Edge TTS 可用音色列表……")
    loop.run_until_complete(load_edge_tts_voices())
    logger.info("[Edge TTS] 读取成功！")
except Exception as e:
    logger.exception(e)
    logger.error("[Edge TTS] 读取失败！")

hook()
loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()
