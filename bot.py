import os
import sys

from loguru import logger

sys.path.append(os.getcwd())

from constants import config

if config.onebot:
    logger.info("检测到 Onebot 配置，将以 Onebot 模式启动……")
    import onebot_bot
elif config.telegram:
    logger.info("检测到 telegram 配置，将以 telegram bot 模式启动……")
    import telegram_bot
else:
    logger.info("检测到 mirai 配置，将以 mirai 模式启动……")
    import ariadne_bot
