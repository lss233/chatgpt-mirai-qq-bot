import os, sys
sys.path.append(os.getcwd())

import asyncio
import itertools
from rich.progress import Progress
from typing import Union, List
import os
from revChatGPT.V1 import Chatbot as V1Chatbot
from revChatGPT.Unofficial import Chatbot as BrowserChatbot
from loguru import logger
from config import Config
from config import OpenAI, OpenAIAuthBase, OpenAIEmailAuth, OpenAISessionTokenAuth

logger.remove()

class BotInfo(asyncio.Lock):
    bot: Union[V1Chatbot, BrowserChatbot]

    mode: str

    queue_size: int = 0

    lastAccessed = None
    """Date when bot is accessed last time"""

    lastFailure = None
    """Date when bot encounter an error last time"""

    def __init__(self, bot, mode):
        self.bot = bot
        self.mode = mode
        super().__init__()
    
    def __str__(self) -> str:
        return self.bot.__str__()

    async def __aenter__(self) -> None:
        self.queue_size = self.queue_size + 1
        return await super().__aenter__()
    
    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.queue_size = self.queue_size - 1
        return await super().__aexit__(exc_type, exc, tb)
    
class BotManager():
    """Bot lifecycle manager."""

    bots: List[BotInfo] = []
    """Bot list"""

    accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth]]
    """Account infos"""
    
    roundrobin: itertools.cycle = None
    
    def __init__(self, accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth]]) -> None:
        self.accounts = accounts
    
    def login(self):
        with Progress() as progress:
            logger.add(sink=progress.console.out, level='TRACE')
            task = progress.add_task("[red]登录 OpenAI", total=len(self.accounts))
            for i, account in enumerate(self.accounts):
                logger.info("正在登录第 {i} 个 OpenAI 账号", i=i + 1)
                try:
                    if account.mode == "proxy":
                        bot = self.__login_V1(account)
                    elif account.mode == "browser":
                        bot = self.__login_browser(account)
                    self.bots.append(bot)
                except Exception as e:
                    logger.exception(e)
                    logger.error("第 {i} 个 OpenAI 账号登录失败！", i = i + 1)
                finally:
                    progress.update(task, advance=1)
        if len(self.bots) < 1:
            logger.error("所有账号均登录失败，无法继续启动！")
            exit(-2)

    def __login_browser(self, account) -> BotInfo :
        logger.info("模式：浏览器直接访问")
        logger.info("这需要你拥有最新版的 Chrome 浏览器。")
        logger.info("即将打开浏览器窗口……")
        logger.info("提示：如果你看见了 Cloudflare 验证码，请手动完成验证。")
        logger.info("如果你持续停留在 Found session token 环节，请使用第三方代理模式。")
        if 'XPRA_PASSWORD' in os.environ:
            logger.info("检测到您正在使用 xpra 虚拟显示环境，请使用你自己的浏览器访问 http://你的IP:14500，密码：{XPRA_PASSWORD}以看见浏览器。", XPRA_PASSWORD=os.environ.get('XPRA_PASSWORD'))
        bot = BrowserChatbot(config=account.dict(exclude_none=True, by_alias=False), conversation_id=None)
        return BotInfo(bot, account.mode)

    def __login_V1(self, account: OpenAIAuthBase) -> BotInfo :
        logger.info("模式：第三方代理")
        bot = V1Chatbot(config=account.dict(exclude_none=True, by_alias=False), conversation_id=None)
        return BotInfo(bot, account.mode)

    def pick(self) -> BotInfo:
        if self.roundrobin is None:
            self.roundrobin = itertools.cycle(self.bots)
        return next(self.roundrobin)