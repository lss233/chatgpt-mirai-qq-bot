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

if constants.config.telegram:
    logger.info("检测到 telegram 配置，将启动 telegram bot 模式……")
    from framework.platforms.telegram_bot import start_task

    bots.append(start_task())
if constants.config.discord:
    logger.info("检测到 discord 配置，将启动 discord bot 模式……")
    from framework.platforms.discord_bot import start_task

    bots.append(start_task())


async def setup_web_service():
    from framework.platforms.onebot_bot import start_http_app
    from framework.platforms.http_service import route as routes_http
    from framework.platforms.http_service_legacy import route as routes_http_legacy
    logger.info("启动 HTTP API……")
    app = await start_http_app()
    routes_http(app)
    routes_http_legacy(app)

    if constants.config.wecom:
        logger.info("检测到 Wecom 配置，将注册 Wecom 路由……")
        from framework.platforms.wecom_bot import route as routes_wecom
        routes_wecom(app)


bots.append(setup_web_service())

loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()
