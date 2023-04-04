import os
import sys

sys.path.append(os.getcwd())
import creart
from asyncio import AbstractEventLoop
import asyncio
from utils.exithooks import hook
from loguru import logger
from constants import config, botManager

hook()

# aiohttp issue
if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


loop = creart.create(AbstractEventLoop)

loop.run_until_complete(botManager.login())

bots = []

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
if config.mirai:
    logger.info("检测到 mirai 配置，将启动 mirai 模式……")
    from platforms.ariadne_bot import start_task
    bots.append(loop.create_task(start_task()))

loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()

