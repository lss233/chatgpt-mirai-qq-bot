import os
import sys


sys.path.append(os.getcwd())

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from loguru import logger

from universal import handle_message

import constants
from framework.accounts import account_manager
from config import Config
import asyncio

if __name__ == '__main__':
    async def response(msg):
        if isinstance(msg, MessageChain):
            logger.debug(f"Say MessageChain with {len(msg)} items")
            for elem in msg:
                if isinstance(elem, Plain):
                    logger.debug(f"Say Plain: {elem}")
                elif isinstance(elem, Image):
                    logger.debug(f"Say Image: {elem}")
        else:
            logger.debug(f"Say Other: {msg}")


    asyncio.run(account_manager.load_accounts(constants.config.accounts))
    asyncio.run(handle_message(
        response,
        f"friend-1234567890",
        "切换AI bing-c",
        is_manager=False
    ))
    asyncio.run(handle_message(
        response,
        f"friend-1234567890",
        "告诉我全球天气情况",
        is_manager=False
    ))
