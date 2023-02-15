import asyncio
import itertools
from typing import Union, List
import os
from loguru import logger
from revChatGPT.V1 import Chatbot as V1Chatbot
from revChatGPT.Unofficial import Chatbot as BrowserChatbot
from config import OpenAI, OpenAIAuthBase


class BotInfo(asyncio.Lock):
    bot: Union[V1Chatbot, BrowserChatbot]

    lastAccessed = None
    """Date when bot is accessed last time"""

    lastFailure = None
    """Date when bot encounter an error last time"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__()
    

    
class BotManager():
    """Bot lifecycle manager."""

    bots: List[BotInfo] = []
    """Bot list"""

    accounts: OpenAI
    """Account infos"""
    
    roundrobin: itertools.cycle = None
    
    def login(self):
        for i, account in enumerate(self.accounts):
            logger.info("正在登录 OpenAI 账号 {i}", i=i)
            if account.mode == "proxy":
                bot = self.__login_V1(account)
            elif account.mode == "browser":
                bot = self.__login_browser(account)
            self.bots.append(bot)

    def __login_browser(self, account) -> BotInfo :
        logger.info("模式：浏览器直接访问")
        logger.info("这需要你拥有最新版的 Chrome 浏览器。")
        logger.info("即将打开浏览器窗口……")
        logger.info("提示：如果你看见了 Cloudflare 验证码，请手动完成验证。")
        logger.info("如果浏览器反复弹出，请阅读项目 FAQ。")
        if 'XPRA_PASSWORD' in os.environ:
            logger.info("检测到您正在使用 xpra，请使用自己的浏览器访问 http://你的IP:14500，密码：{XPRA_PASSWORD}以看见浏览器。", XPRA_PASSWORD=os.environ.get('XPRA_PASSWORD'))
        bot = BrowserChatbot(config=account.dict(exclude_none=True, by_alias=False), conversation_id=None)
        return bot

    def __login_V1(self, account: OpenAIAuthBase) -> BotInfo :
        logger.info("模式：第三方代理")
        bot = V1Chatbot(config=account.dict(exclude_none=True, by_alias=False), conversation_id=None)
        return bot

    def pick(self) -> BotInfo:
        if self.roundrobin is None:
            self.roundrobin = itertools.cycle(self.bots)
        return self.roundrobin