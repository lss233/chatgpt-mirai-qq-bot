import os
import sys

from quart import Quart

sys.path.append(os.getcwd())
from framework.accounts import account_manager

from framework.tts import AzureTTSEngine, TTSEngine, EdgeTTSEngine

import creart
from asyncio import AbstractEventLoop
import asyncio
from framework.utils.exithooks import hook
from loguru import logger
import constants
import threading

hook()

loop = creart.create(AbstractEventLoop)


def setup_cloudflared(app: Quart):
    logger.info("尝试开启 Cloudflare Tunnel……")
    try:
        from pycloudflared import try_cloudflare, remove_executable
        cloudflared_url = try_cloudflare(port=constants.config.http.port)
        for service_name, proto, uri in app.service_routes:
            logger.info(
                f"外部网络访问 {service_name} 地址：{proto}s://{cloudflared_url.tunnel.removeprefix('https://')}{uri}")
    except OSError as e:
        logger.error(f"Cloudflared 开启失败：{e}")
        remove_executable()
    except Exception as e:
        logger.error(f"Cloudflared 开启失败：{e}")


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
    from framework.platforms.onebot_bot import bot, start_http_app
    from framework.platforms.http_service import route as routes_http
    from framework.platforms.http_service_legacy import route as routes_http_legacy
    routes_http(bot.server_app)
    routes_http_legacy(bot.server_app)

    if constants.config.wecom:
        logger.info("检测到 Wecom 配置，将注册 Wecom 路由……")
        from framework.platforms.wecom_bot import route as routes_wecom
        routes_wecom(bot.server_app)

    if constants.config.http.cloudflared:
        threading.Thread(target=setup_cloudflared, args=(bot.server_app,)).start()

    logger.info("启动 HTTP API 中……")
    for service_name, proto, uri in bot.server_app.service_routes:
        logger.info(f"{service_name} 地址：{proto}://{constants.config.http.host}:{constants.config.http.port}{uri}")
    await start_http_app()


bots.append(setup_web_service())

loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()
