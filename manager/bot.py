import datetime
import os
import sys
import time

from requests.exceptions import SSLError

sys.path.append(os.getcwd())

import asyncio
import itertools
from typing import Union, List
import os
from revChatGPT.V1 import Chatbot as V1Chatbot, Error as V1Error
from revChatGPT.Unofficial import Chatbot as BrowserChatbot
from loguru import logger
from config import Config
from config import OpenAIAuthBase, OpenAIEmailAuth, OpenAISessionTokenAuth
import OpenAIAuth
import urllib3.exceptions
import utils.network as network
from tinydb import TinyDB, Query
import hashlib

config = Config.load_config()


class BotInfo(asyncio.Lock):
    id = 0

    account: OpenAIAuthBase

    bot: Union[V1Chatbot, BrowserChatbot]

    mode: str

    queue_size: int = 0

    unused_conversations_pools = {}

    accessed_at = []
    """访问时间，仅保存一小时以内的时间"""

    last_rate_limited = None
    """上一次遇到限流的时间"""

    def __init__(self, bot, mode):
        self.bot = bot
        self.mode = mode
        super().__init__()

    def update_accessed_at(self):
        """更新最后一次请求的时间，用于流量统计"""
        current_time = datetime.datetime.now()
        self.accessed_at.append(current_time)
        self.refresh_accessed_at()

    def refresh_accessed_at(self):
        # 删除栈顶过期的信息
        current_time = datetime.datetime.now()
        while len(self.accessed_at) > 0 and current_time - self.accessed_at[0] > datetime.timedelta(hours=1):
            self.accessed_at.pop(0)

    def update_conversation_pools(self):
        """更新预设对话池"""
        for key in config.presets.keywords.keys():
            if key not in self.unused_conversations_pools:
                self.unused_conversations_pools = []
            preset = config.load_preset(preset)
            self.bot.parent_id = None
            self.bot.conversation_id = None
            for text in preset:
                if text.startswith('ChatGPT:'):
                    pass
                if text.startswith('User:'):
                    text = text.replace('User:', '')
                self.ask(text)

    def ask(self, prompt, conversation_id=None, parent_id=None):
        """向 ChatGPT 发送提问"""
        resp = self.bot.ask(prompt=prompt, conversation_id=conversation_id, parent_id=parent_id)
        if self.mode == 'proxy' or self.mode == 'browserless':
            final_resp = None
            for final_resp in resp: ...
            self.update_accessed_at()
            return final_resp
        else:
            self.update_accessed_at()
            return resp

    def __str__(self) -> str:
        return self.bot.__str__()

    async def __aenter__(self) -> None:
        self.queue_size = self.queue_size + 1
        return await super().__aenter__()

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.queue_size = self.queue_size - 1
        return await super().__aexit__(exc_type, exc, tb)


class BotManager:
    """Bot lifecycle manager."""

    bots: List[BotInfo] = []
    """Bot list"""

    accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth]]
    """Account infos"""

    roundrobin: itertools.cycle = None

    def __init__(self, accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth]]) -> None:
        self.accounts = accounts
        try:
            os.mkdir('data')
            logger.warning(
                "警告：未检测到 data 目录，如果你通过 Docker 部署，请挂载此目录以实现登录缓存，否则可忽略此消息。")
        except:
            pass
        self.cache_db = TinyDB('data/login_caches.json')

    def login(self):
        for i, account in enumerate(self.accounts):
            logger.info("正在登录第 {i} 个 OpenAI 账号", i=i + 1)
            try:
                if account.mode == "proxy" or account.mode == "browserless":
                    bot = self.__login_V1(account)
                elif account.mode == "browser":
                    bot = self.__login_browser(account)
                else:
                    raise Exception("未定义的登录类型：" + account.mode)
                bot.id = i
                bot.account = account
                self.bots.append(bot)
                logger.success("登录成功！", i=i + 1)
                logger.debug("等待 8 秒……")
                time.sleep(8)
            except OpenAIAuth.Error as e:
                logger.error("登录失败! 请检查 IP 、代理或者账号密码是否正确{exc}", exc=e)
            except (SSLError, urllib3.exceptions.MaxRetryError) as e:
                logger.error("登录失败! 连接 OpenAI 服务器失败,请检查网络和本地代理设置！{exc}", exc=e)
            except Exception as e:
                err_msg = str(e)
                if "failed to connect to the proxy server" in err_msg:
                    logger.error("登录失败! 无法连接至本地代理服务器，请检查配置文件中的 proxy 是否正确！{exc}", exc=e)
                elif "All login method failed" in err_msg:
                    logger.error("登录失败! 所有登录方法均已失效,请检查 IP、代理或者登录信息是否正确{exc}", exc=e)
                else:
                    logger.error("未知错误：")
                    logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有账号均登录失败，无法继续启动！")
            exit(-2)
        logger.success(f"成功登录 {len(self.bots)}/{len(self.accounts)} 个账号！")

    def __login_browser(self, account) -> BotInfo:
        logger.info("模式：浏览器登录")
        logger.info("这需要你拥有最新版的 Chrome 浏览器。")
        logger.info("即将打开浏览器窗口……")
        logger.info("提示：如果你看见了 Cloudflare 验证码，请手动完成验证。")
        logger.info("如果你持续停留在 Found session token 环节，请使用无浏览器登录模式。")
        if 'XPRA_PASSWORD' in os.environ:
            logger.info(
                "检测到您正在使用 xpra 虚拟显示环境，请使用你自己的浏览器访问 http://你的IP:14500，密码：{XPRA_PASSWORD}以看见浏览器。",
                XPRA_PASSWORD=os.environ.get('XPRA_PASSWORD'))
        bot = BrowserChatbot(config=account.dict(exclude_none=True, by_alias=False))
        return BotInfo(bot, account.mode)

    def __save_login_cache(self, account: OpenAIAuthBase, cache: dict):
        """保存登录缓存"""
        account_sha = hashlib.sha256(account.json().encode('utf8')).hexdigest()
        q = Query()
        self.cache_db.upsert({'account': account_sha, 'cache': cache}, q.account == account_sha)

    def __load_login_cache(self, account):
        """读取登录缓存"""
        account_sha = hashlib.sha256(account.json().encode('utf8')).hexdigest()
        q = Query()
        cache = self.cache_db.get(q.account == account_sha)
        return cache['cache'] if cache is not None else dict()

    def __login_V1(self, account: OpenAIAuthBase) -> BotInfo:
        logger.info("模式：无浏览器登录")
        cached_account = dict(self.__load_login_cache(account), **account.dict())
        config = dict()
        if account.proxy is not None:
            logger.info(f"正在检查代理配置：{account.proxy}")
            from urllib.parse import urlparse
            proxy_addr = urlparse(account.proxy)
            if not network.is_open(proxy_addr.hostname, proxy_addr.port):
                raise Exception("failed to connect to the proxy server")
            config['proxy'] = account.proxy

        # 我承认这部分代码有点蠢
        def __V1_check_auth(bot) -> bool:
            try:
                bot.get_conversations(0, 1)
                return True
            except (V1Error, KeyError) as e:
                return False

        def get_access_token(bot: V1Chatbot):
            return bot.session.headers.get('Authorization').removeprefix('Bearer ')

        if 'access_token' in cached_account:
            logger.info("尝试使用 access_token 登录中...")
            config['access_token'] = cached_account['access_token']
            bot = V1Chatbot(config=config)
            if __V1_check_auth(bot):
                return BotInfo(bot, account.mode)

        if 'session_token' in cached_account:
            logger.info("尝试使用 session_token 登录中...")
            config.pop('access_token', None)
            config['session_token'] = cached_account['session_token']
            bot = V1Chatbot(config=config)
            self.__save_login_cache(account=account, cache={
                "session_token": config['session_token'],
                "access_token": get_access_token(bot),
            })
            if __V1_check_auth(bot):
                return BotInfo(bot, account.mode)

        if 'password' in cached_account:
            logger.info("尝试使用 email + password 登录中...")
            config.pop('access_token', None)
            config.pop('session_token', None)
            config['email'] = cached_account['email']
            config['password'] = cached_account['password']
            bot = V1Chatbot(config=config)
            self.__save_login_cache(account=account, cache={
                "session_token": bot.config['session_token'],
                "access_token": get_access_token(bot)
            })
            if __V1_check_auth(bot):
                return BotInfo(bot, account.mode)
        # Invalidate cache
        self.__save_login_cache(account=account, cache={})
        raise Exception("All login method failed")

    def pick(self) -> BotInfo:
        if self.roundrobin is None:
            self.roundrobin = itertools.cycle(self.bots)
        return next(self.roundrobin)
