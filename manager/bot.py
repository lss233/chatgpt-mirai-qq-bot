import datetime
import hashlib
import itertools
import os
import time
import urllib.request
from typing import List, Dict
from urllib.parse import urlparse

import OpenAIAuth
import aiohttp
import openai
import requests
import urllib3.exceptions
from aiohttp import ClientConnectorError
from dateutil.relativedelta import relativedelta
from loguru import logger
from poe import Client as PoeClient
from requests.exceptions import SSLError, RequestException
from revChatGPT import V1
from revChatGPT.V1 import AsyncChatbot as V1Chatbot
from revChatGPT.typings import Error as V1Error
from tinydb import TinyDB, Query

import utils.network as network
from chatbot.Unofficial import AsyncChatbot as BrowserChatbot
from chatbot.chatgpt import ChatGPTBrowserChatbot
from config import OpenAIAuthBase, OpenAIAPIKey, Config, BingCookiePath, BardCookiePath, YiyanCookiePath, ChatGLMAPI, \
    PoeCookieAuth
from exceptions import NoAvailableBotException, APIKeyNoFundsError


class BotManager:
    """Bot lifecycle manager."""

    bots: Dict[str, List] = {
        "chatgpt-web": [],
        "openai-api": [],
        "poe-web": [],
        "bing-cookie": [],
        "bard-cookie": [],
        "yiyan-cookie": [],
    }
    """Bot list"""

    openai: List[OpenAIAuthBase]
    """OpenAI Account infos"""

    bing: List[BingCookiePath]
    """Bing Account Infos"""

    bard: List[BardCookiePath]
    """Bard Account Infos"""

    poe: List[PoeCookieAuth]
    """Poe Account infos"""

    yiyan: List[YiyanCookiePath]
    """Yiyan Account Infos"""

    chatglm: List[ChatGLMAPI]
    """chatglm Account Infos"""

    roundrobin: Dict[str, itertools.cycle] = {}

    def __init__(self, config: Config) -> None:
        self.config = config
        self.openai = config.openai.accounts if config.openai else []
        self.bing = config.bing.accounts if config.bing else []
        self.bard = config.bard.accounts if config.bard else []
        self.poe = config.poe.accounts if config.poe else []
        self.yiyan = config.yiyan.accounts if config.yiyan else []
        self.chatglm = config.chatglm.accounts if config.chatglm else []
        try:
            os.mkdir('data')
            logger.warning(
                "警告：未检测到 data 目录，如果你通过 Docker 部署，请挂载此目录以实现登录缓存，否则可忽略此消息。")
        except:
            pass
        self.cache_db = TinyDB('data/login_caches.json')

    async def login(self):
        self.bots = {
            "chatgpt-web": [],
            "openai-api": [],
            "poe-web": [],
            "bing-cookie": [],
            "bard-cookie": [],
            "yiyan-cookie": [],
            "chatglm-api": [],
        }
        self.__setup_system_proxy()
        if len(self.bing) > 0:
            self.login_bing()
        if len(self.poe) > 0:
            self.login_poe()
        if len(self.bard) > 0:
            self.login_bard()
        if len(self.openai) > 0:
            if self.config.openai.browserless_endpoint:
                V1.BASE_URL = self.config.openai.browserless_endpoint or V1.BASE_URL
            logger.info(f"当前的 browserless_endpoint 为：{V1.BASE_URL}")

            if V1.BASE_URL == 'https://bypass.duti.tech/api/':
                logger.error("检测到你还在使用旧的 browserless_endpoint，已为您切换。")
                V1.BASE_URL = "https://bypass.churchless.tech/api/"

            if not V1.BASE_URL.endswith("api/"):
                logger.warning(
                    f"提示：你可能要将 browserless_endpoint 修改为 \"{self.config.openai.browserless_endpoint}api/\"")

            if self.config.openai.api_endpoint:
                openai.api_base = self.config.openai.api_endpoint or openai.api_base
            logger.info(f"当前的 api_endpoint 为：{openai.api_base}")

            await self.login_openai()
        if len(self.yiyan) > 0:
            self.login_yiyan()
        if len(self.chatglm) > 0:
            self.login_chatglm()
        count = sum(len(v) for v in self.bots.values())
        if count < 1:
            logger.error("没有登录成功的账号，程序无法启动！")
            exit(-2)
        else:
            # 输出登录状况
            for k, v in self.bots.items():
                logger.info(f"AI 类型：{k} - 可用账号： {len(v)} 个")
        # 自动推测默认 AI
        if not self.config.response.default_ai:
            if len(self.bots['poe-web']) > 0:
                self.config.response.default_ai = 'poe-chatgpt'
            elif len(self.bots['chatgpt-web']) > 0:
                self.config.response.default_ai = 'chatgpt-web'
            elif len(self.bots['openai-api']) > 0:
                self.config.response.default_ai = 'chatgpt-api'
            elif len(self.bots['bing-cookie']) > 0:
                self.config.response.default_ai = 'bing'
            elif len(self.bots['bard-cookie']) > 0:
                self.config.response.default_ai = 'bard'
            elif len(self.bots['yiyan-cookie']) > 0:
                self.config.response.default_ai = 'yiyan'
            elif len(self.bots['chatglm-api']) > 0:
                self.config.response.default_ai = 'chatglm-api'
            else:
                self.config.response.default_ai = 'chatgpt-web'

    def login_bing(self):
        os.environ['BING_PROXY_URL'] = self.config.bing.bing_endpoint
        for i, account in enumerate(self.bing):
            logger.info("正在解析第 {i} 个 Bing 账号", i=i + 1)
            if proxy := self.__check_proxy(account.proxy):
                account.proxy = proxy
            try:
                self.bots["bing-cookie"].append(account)
                logger.success("解析成功！", i=i + 1)
            except Exception as e:
                logger.error("解析失败：")
                logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有 Bing 账号均解析失败！")
        logger.success(f"成功解析 {len(self.bots['bing-cookie'])}/{len(self.bing)} 个 Bing 账号！")

    def login_bard(self):
        for i, account in enumerate(self.bard):
            logger.info("正在解析第 {i} 个 Bard 账号", i=i + 1)
            if proxy := self.__check_proxy(account.proxy):
                account.proxy = proxy
            try:
                self.bots["bard-cookie"].append(account)
                logger.success("解析成功！", i=i + 1)
            except Exception as e:
                logger.error("解析失败：")
                logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有 Bard 账号均解析失败！")
        logger.success(f"成功解析 {len(self.bots['bard-cookie'])}/{len(self.bing)} 个 Bard 账号！")

    def login_poe(self):
        def poe_check_auth(client: PoeClient) -> bool:
            try:
                response = client.get_bot_names()
                logger.debug(f"poe bot is running. bot names -> {response}")
                return True
            except KeyError:
                return False

        try:
            for i, account in enumerate(self.poe):
                logger.info("正在解析第 {i} 个 poe web 账号", i=i + 1)
                if proxy := self.__check_proxy(account.proxy):
                    account.proxy = proxy
                bot = PoeClient(token=account.p_b, proxy=account.proxy)
                if poe_check_auth(bot):
                    self.bots["poe-web"].append(bot)
                    logger.success("解析成功！", i=i + 1)
        except Exception as e:
            logger.error("解析失败：")
            logger.exception(e)
        if len(self.bots["poe-web"]) < 1:
            logger.error("所有 Poe 账号均解析失败！")
        logger.success(f"成功解析 {len(self.bots['poe-web'])}/{len(self.poe)} 个 poe web 账号！")

    def login_yiyan(self):
        for i, account in enumerate(self.yiyan):
            logger.info("正在解析第 {i} 个 文心一言 账号", i=i + 1)
            if proxy := self.__check_proxy(account.proxy):
                account.proxy = proxy
            try:
                self.bots["yiyan-cookie"].append(account)
                logger.success("解析成功！", i=i + 1)
            except Exception as e:
                logger.error("解析失败：")
                logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有 文心一言 账号均解析失败！")
        logger.success(f"成功解析 {len(self.bots['yiyan-cookie'])}/{len(self.yiyan)} 个 文心一言 账号！")

    def login_chatglm(self):
        for i, account in enumerate(self.chatglm):
            logger.info("正在解析第 {i} 个 ChatGLM 账号", i=i + 1)
            try:
                self.bots["chatglm-api"].append(account)
                logger.success("解析成功！", i=i + 1)
            except Exception as e:
                logger.error("解析失败：")
                logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有 ChatGLM 账号均解析失败！")
        logger.success(f"成功解析 {len(self.bots['chatglm-api'])}/{len(self.chatglm)} 个 ChatGLM 账号！")

    async def login_openai(self):
        counter = 0
        for i, account in enumerate(self.openai):
            logger.info("正在登录第 {i} 个 OpenAI 账号", i=i + 1)
            try:
                if isinstance(account, OpenAIAPIKey):
                    bot = await self.__login_openai_apikey(account)
                    self.bots["openai-api"].append(bot)
                elif account.mode == "proxy" or account.mode == "browserless":
                    bot = await self.__login_V1(account)
                    self.bots["chatgpt-web"].append(bot)
                elif account.mode == "browser":
                    bot = self.__login_browser(account)
                    self.bots["chatgpt-web"].append(bot)
                else:
                    raise Exception("未定义的登录类型：" + account.mode)
                bot.id = i
                bot.account = account
                logger.success("登录成功！", i=i + 1)
                counter = counter + 1
            except OpenAIAuth.Error as e:
                logger.error("登录失败! 请检查 IP 、代理或者账号密码是否正确{exc}", exc=e)
            except (RequestException, SSLError, urllib3.exceptions.MaxRetryError, ClientConnectorError) as e:
                logger.error("登录失败! 连接 OpenAI 服务器失败,请更换代理节点重试！{exc}", exc=e)
            except APIKeyNoFundsError:
                logger.error("登录失败! API 账号余额不足，无法继续使用。")
            except Exception as e:
                err_msg = str(e)
                if "failed to connect to the proxy server" in err_msg:
                    logger.error("{exc}", exc=e)
                elif "All login method failed" in err_msg:
                    logger.error("登录失败! 所有登录方法均已失效,请检查 IP、代理或者登录信息是否正确{exc}", exc=e)
                else:
                    logger.error("未知错误：")
                    logger.exception(e)
        if len(self.bots) < 1:
            logger.error("所有 OpenAI 账号均登录失败！")
        logger.success(f"成功登录 {counter}/{len(self.openai)} 个 OpenAI 账号！")

    def __login_browser(self, account) -> ChatGPTBrowserChatbot:
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
        return ChatGPTBrowserChatbot(bot, account.mode)

    def __setup_system_proxy(self):

        system_proxy = None
        for url in urllib.request.getproxies().values():
            try:
                system_proxy = self.__check_proxy(url)
                if system_proxy is not None:
                    break
            except:
                pass
        if system_proxy is not None:
            openai.proxy = system_proxy

    def __check_proxy(self, proxy):
        if proxy is not None:
            logger.info(f"[代理测试] 正在检查代理配置：{proxy}")
            proxy_addr = urlparse(proxy)
            if not network.is_open(proxy_addr.hostname, proxy_addr.port):
                raise Exception("登录失败! 无法连接至本地代理服务器，请检查配置文件中的 proxy 是否正确！")
            requests.get("http://www.gstatic.com/generate_204", proxies={
                "https": proxy,
                "http": proxy
            })
            logger.success(f"[代理测试] 连接成功！")
            return proxy
        else:
            return openai.proxy

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

    async def __login_V1(self, account: OpenAIAuthBase) -> ChatGPTBrowserChatbot:
        logger.info("模式：无浏览器登录")
        cached_account = dict(self.__load_login_cache(account), **account.dict())
        config = dict()
        if proxy := self.__check_proxy(account.proxy):
            config['proxy'] = proxy
        if cached_account.get('paid'):
            config['paid'] = True
        if cached_account.get('gpt4'):
            config['model'] = 'gpt-4'
        if cached_account.get('model'):  # Ready for backward-compatibility & forward-compatibility
            config['model'] = cached_account.get('model')

        # 我承认这部分代码有点蠢
        async def __V1_check_auth() -> bool:
            try:
                await bot.get_conversations(0, 1)
                return True
            except (V1Error, KeyError):
                return False

        def get_access_token():
            return bot.session.headers.get('Authorization').removeprefix('Bearer ')

        if cached_account.get('access_token'):
            logger.info("尝试使用 access_token 登录中...")
            config['access_token'] = cached_account.get('access_token')
            bot = V1Chatbot(config=config)
            if await __V1_check_auth():
                return ChatGPTBrowserChatbot(bot, account.mode)

        if cached_account.get('session_token'):
            logger.info("尝试使用 session_token 登录中...")
            config.pop('access_token', None)
            config['session_token'] = cached_account.get('session_token')
            bot = V1Chatbot(config=config)
            self.__save_login_cache(account=account, cache={
                "session_token": config['session_token'],
                "access_token": get_access_token(),
            })
            if await __V1_check_auth():
                return ChatGPTBrowserChatbot(bot, account.mode)

        if cached_account.get('password'):
            logger.info("尝试使用 email + password 登录中...")
            logger.warning("警告：该方法已不推荐使用，建议使用 access_token 登录。")
            config.pop('access_token', None)
            config.pop('session_token', None)
            config['email'] = cached_account.get('email')
            config['password'] = cached_account.get('password')
            bot = V1Chatbot(config=config)
            self.__save_login_cache(account=account, cache={
                "session_token": bot.config.get('session_token'),
                "access_token": get_access_token()
            })
            if await __V1_check_auth():
                return ChatGPTBrowserChatbot(bot, account.mode)
        # Invalidate cache
        self.__save_login_cache(account=account, cache={})
        raise Exception("All login method failed")

    async def check_api_info(self, account):
        async with aiohttp.ClientSession(conn_timeout=30, read_timeout=30, trust_env=True,
                                         connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            timing_start_at = time.time()
            session.headers.add("Authorization", f"Bearer {account.api_key}")

            resp = await session.get(f"{openai.api_base}/dashboard/billing/credit_grants", proxy=account.proxy)
            resp = await resp.json()

            if 'error' in resp:
                raise Exception(resp['error']['message'])

            grant_available = resp.get("total_available")
            grant_used = resp.get("total_used")

            resp = await session.get(f"{openai.api_base}/dashboard/billing/subscription", proxy=account.proxy)
            resp = await resp.json()
            has_payment_method = resp.get('has_payment_method')
            hard_limit_usd = resp.get('hard_limit_usd')

            current_month = datetime.datetime.now().replace(day=1)
            next_month = current_month + relativedelta(months=1)

            start_date = current_month.strftime('%Y-%m-%d')
            end_date = next_month.strftime('%Y-%m-%d')
            resp = await session.get(
                f"{openai.api_base}/dashboard/billing/usage?start_date={start_date}&end_date={end_date}",
                proxy=account.proxy)
            resp = await resp.json()
            total_usage = resp.get("total_usage") / 100
            timing_stop_at = time.time()
            logger.debug(f"本次查询平均延迟：{round((timing_stop_at - timing_start_at) / 3, 2)}s")
        return grant_used, grant_available, has_payment_method, total_usage, hard_limit_usd

    async def __login_openai_apikey(self, account):
        logger.info("尝试使用 api_key 登录中...")
        if proxy := self.__check_proxy(account.proxy):
            openai.proxy = proxy
            account.proxy = proxy
        logger.info("当前检查的 API Key 为：" + account.api_key[:8] + "******" + account.api_key[-4:])

        grant_used, grant_available, has_payment_method, total_usage, hard_limit_usd = await self.check_api_info(
            account)

        total_available = grant_available

        if has_payment_method:
            logger.success(f"查询到此 API 为订阅用户，本月已用：{total_usage}美元，硬上限：{hard_limit_usd}美元。")
            total_available = total_available + hard_limit_usd - total_usage

        logger.success(f"查询到 API 总可用余额： {total_available}美元")
        if int(total_available) <= 0:
            raise APIKeyNoFundsError("API 余额不足，无法继续使用。")
        return account

    def pick(self, type: str):
        if not type in self.roundrobin:
            self.roundrobin[type] = itertools.cycle(self.bots[type])
        if len(self.bots[type]) == 0:
            raise NoAvailableBotException(type)
        return next(self.roundrobin[type])
