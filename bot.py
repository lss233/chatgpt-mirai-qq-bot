import os
import sys


sys.path.append(os.getcwd())
from framework.accounts import account_manager

from framework.tts import AzureTTSEngine, TTSEngine, EdgeTTSEngine

import creart
from asyncio import AbstractEventLoop
import asyncio
from framework.utils.exithooks import hook
from loguru import logger
import constants

hook()

loop = creart.create(AbstractEventLoop)

tasks = []
if constants.config.azure:
    tasks.append(loop.create_task(TTSEngine.register("azure", AzureTTSEngine(constants.config.azure))))

tasks.extend(
    (
        loop.create_task(
            TTSEngine.register("edge", EdgeTTSEngine())
        ),
        loop.create_task(
            account_manager.load_accounts(constants.config.accounts)
        ),
    )
)
loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

bots = []

if constants.config.mirai:
    logger.info("检测到 mirai 配置，将启动 mirai 模式……")
    from framework.platforms.ariadne_bot import start_task

    bots.append(start_task())

if constants.config.onebot:
    logger.info("检测到 Onebot 配置，将启动 Onebot 模式……")
    from framework.platforms.onebot_bot import start_task

    bots.append(start_task())
if constants.config.telegram:
    logger.info("检测到 telegram 配置，将启动 telegram bot 模式……")
    from framework.platforms.telegram_bot import start_task

    bots.append(start_task())
if constants.config.discord:
    logger.info("检测到 discord 配置，将启动 discord bot 模式……")
    from framework.platforms.discord_bot import start_task

    bots.append(start_task())
if constants.config.http:
    logger.info("检测到 http 配置，将启动 http service 模式……")
    from framework.platforms.http_service import start_task

    bots.append(start_task())
if constants.config.wecom:
    logger.info("检测到 Wecom 配置，将启动 Wecom Bot 模式……")
    from framework.platforms.wecom_bot import start_task

    bots.append(start_task())

loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()
