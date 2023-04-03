import os
import sys
import threading
import time

sys.path.append(os.getcwd())

import asyncio
from utils.exithooks import hook
from loguru import logger
from constants import config

hook()

# aiohttp issue
if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bots = []

if config.onebot:
    logger.info("检测到 Onebot 配置，将启动 Onebot 模式……")
    from platforms.onebot_bot import main
    bots.append(main)
if config.telegram:
    logger.info("检测到 telegram 配置，将启动 telegram bot 模式……")
    from platforms.telegram_bot import main
    bots.append(main)
if config.discord:
    logger.info("检测到 discord 配置，将启动 discord bot 模式……")
    from platforms.discord_bot import main
    bots.append(main)
if config.http:
    logger.info("检测到 http 配置，将启动 http service 模式……")
    from platforms.http_service import main
    bots.append(main)
if config.mirai:
    logger.info("检测到 mirai 配置，将启动 mirai 模式……")
    from platforms.ariadne_bot import main
    bots.append(main)
if len(bots) > 1:
    logger.info("进入多线程模式")
    bot_threads = []
    for main in bots:
        bot_threads.append(threading.Thread(target=main))
    for thread in bot_threads:
        thread.start()
        time.sleep(10)
    for thread in bot_threads:
        thread.join()
elif len(bots) == 1:
    logger.info("进入单线程模式")
    bots.pop()()
else:
    logger.error("配置无效，请检查配置！")
