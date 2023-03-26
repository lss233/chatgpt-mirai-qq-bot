import os
import sys

sys.path.append(os.getcwd())

from loguru import logger
from constants import config

if config.onebot:
    logger.info("检测到 Onebot 配置，将以 Onebot 模式启动……")
    from platforms.onebot_bot import main
elif config.telegram:
    logger.info("检测到 telegram 配置，将以 telegram bot 模式启动……")
    from platforms.telegram_bot import main
elif config.discord:
    logger.info("检测到 discord 配置，将以 discord bot 模式启动……")
    from platforms.discord_bot import main
else:
    logger.info("检测到 mirai 配置，将以 mirai 模式启动……")
    from platforms.ariadne_bot import main

# 如果想要同时支持多平台，在这里开多线程就行了
main()
