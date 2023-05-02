import os
import sys
from typing import Type

sys.path.append(os.getcwd())
from accounts import account_manager
from adapter.baidu.yiyan import YiyanAdapter
from adapter.botservice import BotAdapter
from adapter.chatgpt.api import ChatGPTAPIAdapter
from adapter.chatgpt.web import ChatGPTWebAdapter
from adapter.claude.slack import ClaudeInSlackAdapter
from adapter.google.bard import BardAdapter
from adapter.ms.bing import BingAdapter
from adapter.quora.poe_web import PoeAdapter
from adapter.thudm.chatglm_6b import ChatGLM6BAdapter


import creart
from asyncio import AbstractEventLoop
import asyncio
from utils.exithooks import hook
from loguru import logger
from config import Config
import constants

hook()


def register_llm(adapter: Type[BotAdapter]):
    adapter.register()


register_llm(ChatGPTWebAdapter)
register_llm(YiyanAdapter)
register_llm(ChatGPTAPIAdapter)
register_llm(ClaudeInSlackAdapter)
register_llm(BardAdapter)
register_llm(BingAdapter)
register_llm(PoeAdapter)
register_llm(ChatGLM6BAdapter)
constants.config = Config.load_config()
constants.config.scan_presets()

loop = creart.create(AbstractEventLoop)

# loop.run_until_complete(botManager.login())
loop.run_until_complete(account_manager.load_accounts(constants.config.accounts))
bots = []

if constants.config.mirai:
    logger.info("检测到 mirai 配置，将启动 mirai 模式……")
    from platforms.ariadne_bot import start_task

    bots.append(loop.create_task(start_task()))

if constants.config.onebot:
    logger.info("检测到 Onebot 配置，将启动 Onebot 模式……")
    from platforms.onebot_bot import start_task

    bots.append(loop.create_task(start_task()))
if constants.config.telegram:
    logger.info("检测到 telegram 配置，将启动 telegram bot 模式……")
    from platforms.telegram_bot import start_task

    bots.append(loop.create_task(start_task()))
if constants.config.discord:
    logger.info("检测到 discord 配置，将启动 discord bot 模式……")
    from platforms.discord_bot import start_task

    bots.append(loop.create_task(start_task()))
if constants.config.http:
    logger.info("检测到 http 配置，将启动 http service 模式……")
    from platforms.http_service import start_task

    bots.append(loop.create_task(start_task()))
if constants.config.wecom:
    logger.info("检测到 Wecom 配置，将启动 Wecom Bot 模式……")
    from platforms.wecom_bot import start_task

    bots.append(loop.create_task(start_task()))

loop.run_until_complete(asyncio.gather(*bots))
loop.run_forever()
