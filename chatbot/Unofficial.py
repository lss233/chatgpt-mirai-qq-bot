import json
import logging
import re
from typing import Optional

import asyncio
import uuid
from time import sleep

import undetected_chromedriver as uc
from httpx import AsyncClient
from loguru import logger
from requests.exceptions import HTTPError
from selenium.common import UnableToSetCookieException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import requests
#from urllib3.util import ssl_
#from urllib3 import poolmanager
#from requests.adapters import HTTPAdapter
#import ssl


# Disable all logging
logging.basicConfig(level=logging.ERROR)

BASE_URL = "https://chat.openai.com/"


class Chrome(uc.Chrome):
    def __del__(self):
        self.quit()


class AsyncChatbot:
    def __init__(
            self,
            config,
            conversation_id=None,
            parent_id=None,
            no_refresh=False,
    ) -> None:
        self.config = config

        self.conversation_id = conversation_id
        self.parent_id = parent_id
        self.conversation_mapping = {}
        self.conversation_id_prev_queue = []
        self.parent_id_prev_queue = []
        self.isMicrosoftLogin = False
        self.authheaders = {}
        self.access_token_auth = None

        if config and "access_token" in config:
            self.access_token_auth = config["access_token"]

        if "email" in config and "password" in config:
            if type(config["email"]) != str:
                raise Exception("Email must be a string!")
            if type(config["password"]) != str:
                raise Exception("Password must be a string!")
            self.email = config["email"]
            self.password = config["password"]
            if "isMicrosoftLogin" in config and config["isMicrosoftLogin"] is True:
                self.isMicrosoftLogin = True
                self.__microsoft_login()
            else:
                self.__email_login()
        else:
            raise Exception("Invalid config!")

    async def __retry_refresh(self):
        retries = 5
        refresh = True
        while refresh:
            try:
                self.__refresh_session()
                refresh = False
            except Exception as exc:
                if retries == 0:
                    raise exc
                retries -= 1

    def __check_response(self, response):
        if response.status_code != 200:
            print(response.text)
            raise Exception("Response code error: ", response.status_code)

    async def __refresh_session(self, session_token=None, timeout=3600):
        if self.isMicrosoftLogin:
            print("Attempting to re-authenticate...")
            self.__microsoft_login()
        else:
            self.__email_login()


    def __microsoft_login(self) -> None:
        """
        Login to OpenAI via Microsoft Login Authentication.

        :return: None
        """
        driver = None
        try:
            # Open the browser
            self.cf_cookie_found = False
            self.puid_cookie_found = False
            self.session_cookie_found = False
            self.agent_found = False
            self.cf_clearance = None
            self.puid_cookie = None
            self.user_agent = None
            self.sec_ch_ua = None
            options = self.__get_ChromeOptions()
            logger.info("启动浏览器登录中...")
            driver = uc.Chrome(
                enable_cdp_events=True,
                options=options,
                driver_executable_path=self.config.get("driver_exec_path"),
                browser_executable_path=self.config.get("browser_exec_path"),
            )
            logger.info("浏览器启动成功")
            driver.add_cdp_listener(
                "Network.responseReceivedExtraInfo",
                lambda msg: self.__detect_cookies(msg),
            )
            driver.add_cdp_listener(
                "Network.requestWillBeSentExtraInfo",
                lambda msg: self.__detect_user_agent(msg),
            )
            driver.get(BASE_URL)
            while not self.agent_found or not self.cf_cookie_found:
                sleep(5)
            
            # Wait for the login button to appear
            logger.info("正在寻找 Log in 按钮")
            WebDriverWait(driver, 120).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button/div[contains(text(), 'Log in')]"),
                ),
            )
            # Click the login button
            logger.info("正在点击 Log in 按钮")
            driver.find_element(
                by=By.XPATH,
                value="//button/div[contains(text(), 'Log in')]",
            ).click()
            # Wait for the Login with Microsoft button to be clickable
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@data-provider='windowslive']"),
                ),
            )
            logger.info("正在点击通过 Microsoft 登录按钮")
            # Click the Login with Microsoft button
            driver.find_element(
                by=By.XPATH,
                value="//button[@data-provider='windowslive']",
            ).click()
            # Wait for the email input field to appear
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[@type='email']"),
                ),
            )
            # Enter the email
            logger.info("正在输入邮箱")
            driver.find_element(
                by=By.XPATH,
                value="//input[@type='email']",
            ).send_keys(self.config["email"])
            # Wait for the Next button to be clickable
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@type='submit']"),
                ),
            )
            # Click the Next button
            driver.find_element(
                by=By.XPATH,
                value="//input[@type='submit']",
            ).click()
            # Wait for the password input field to appear
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[@type='password']"),
                ),
            )
            # Enter the password
            logger.info("正在输入密码")
            driver.find_element(
                by=By.XPATH,
                value="//input[@type='password']",
            ).send_keys(self.config["password"])
            # Wait for the Sign in button to be clickable
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@type='submit']"),
                ),
            )
            # Click the Sign in button
            logger.info("正在点击提交")
            driver.find_element(
                by=By.XPATH,
                value="//input[@type='submit']",
            ).click()
            # Wait for the Allow button to appear
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@type='submit']"),
                ),
            )
            # click Yes button
            driver.find_element(
                by=By.XPATH,
                value="//input[@type='submit']",
            ).click()
            # wait for input box to appear (to make sure we're signed in)
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//textarea"),
                ),
            )
            logger.success("登录成功")

            self._set_auth_headers()

        finally:
            # Close the browser
            if driver is not None:
                driver.quit()
                del driver

    def __email_login(self) -> None:
        """
        Login to OpenAI via Email/Password Authentication and 2Captcha.

        :return: None
        """
        # Open the browser
        driver = None
        try:
            self.cf_cookie_found = False
            self.puid_cookie_found = False
            self.session_cookie_found = False
            self.agent_found = False
            self.cf_clearance = None
            self.puid_cookie = None
            self.user_agent = None
            options = self.__get_ChromeOptions()
            logger.info("启动浏览器登录中...")
            driver = uc.Chrome(
                enable_cdp_events=True,
                options=options,
                driver_executable_path=self.config.get("driver_exec_path"),
                browser_executable_path=self.config.get("browser_exec_path"),
            )
            logger.info("浏览器启动成功")
            driver.add_cdp_listener(
                "Network.responseReceivedExtraInfo",
                lambda msg: self.__detect_cookies(msg),
            )
            driver.add_cdp_listener(
                "Network.requestWillBeSentExtraInfo",
                lambda msg: self.__detect_user_agent(msg),
            )
            driver.get(BASE_URL)

            
            # Wait for the login button to appear
            logger.info("正在寻找 Log in 按钮")
            WebDriverWait(driver, 120).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button/div[contains(text(), 'Log in')]"),
                ),
            )
            # Click the login button
            logger.info("正在点击 Log in 按钮")
            driver.find_element(
                by=By.XPATH,
                value="//button/div[contains(text(), 'Log in')]",
            ).click()
            # Wait for the email input field to appear
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.ID, "username"),
                ),
            )
            # Enter the email
            logger.info("正在输入邮箱")
            driver.find_element(by=By.ID, value="username").send_keys(
                self.config["email"],
            )
            # Wait for the Continue button to be clickable
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@type='submit']"),
                ),
            )
            # Click the Continue button
            driver.find_element(
                by=By.XPATH,
                value="//button[@type='submit']",
            ).click()
            # Wait for the password input field to appear
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.ID, "password"),
                ),
            )
            # Enter the password
            logger.info("正在输入密码")
            driver.find_element(by=By.ID, value="password").send_keys(
                self.config["password"],
            )
            # Wait for the Sign in button to be clickable
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@type='submit']"),
                ),
            )
            # Click the Sign in button
            driver.find_element(
                by=By.XPATH,
                value="//button[@type='submit']",
            ).click()
            # wait for input box to appear (to make sure we're signed in)
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//textarea"),
                ),
            )
            logger.info("登录成功")
            
            
            while not self.session_cookie_found:
                logger.info("正在等待session cookie")
                sleep(5)
            while not self.agent_found or not self.cf_cookie_found:
                logger.info("正在等待cf_clearance cookie")
                sleep(5)  

            '''
                logger.info("正在获取access token")
                driver.get("https://chat.openai.com/api/auth/session")
                try:
                    WebDriverWait(driver, 60).until(lambda d: json_contains_key(d.page_source, "accessToken"))
                    self.access_token_auth = json.loads(driver.page_source)["accessToken"]
                
                except Exception as e:
                    logger.error(f"获取access token失败: {e}")
                    pass
                while not self.access_token_auth:
                    logger.info("正在等待access_token")
                    sleep(5) 
            '''
            self._set_auth_headers()
            
        finally:
            if driver is not None:
                # Close the browser
                driver.quit()
                del driver

    def __get_ChromeOptions(self):
        options = uc.ChromeOptions()
        options.add_argument("--start_maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disable-gpu")
        options.add_argument('--enable-quic')
        options.add_argument('--origin-to-force-quic-on=chat.openai.com:443')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if self.config.get("proxy", "") != "":
            options.add_argument("--proxy-server=" + self.config["proxy"])
        return options

    def __get_cf_cookies(self) -> None:
        """
        Get cloudflare cookies.

        :return: None
        """
        driver = None
        try:
            self.cf_cookie_found = False
            self.agent_found = False
            self.puid_cookie_found = False
            self.cf_clearance = None
            self.puid_cookie = None
            self.user_agent = None
            options = self.__get_ChromeOptions()
            logger.info("获取 cf_clearance 中，正在启动浏览器……")
            driver = uc.Chrome(
                enable_cdp_events=True,
                options=options,
                driver_executable_path=self.config.get("driver_exec_path"),
                browser_executable_path=self.config.get("browser_exec_path"),
            )

            logger.info("浏览器已启动，加载页面中……")
            driver.add_cdp_listener(
                "Network.responseReceivedExtraInfo",
                lambda msg: self.__detect_cookies(msg),
            )
            driver.add_cdp_listener(
                "Network.requestWillBeSentExtraInfo",
                lambda msg: self.__detect_user_agent(msg),
            )

            driver.get("https://chat.openai.com/api/auth/session")

            for cookie in driver.get_cookies():
                if cookie['name'] == 'cf_clearance':
                    self.cf_clearance = cookie['value']
                    self.cf_cookie_found = True
        finally:
            # Close the browser
            if driver is not None:
                driver.quit()
                del driver

    def __detect_cookies(self, message):
        if "params" in message:
            if "headers" in message["params"]:
                if "set-cookie" in message["params"]["headers"]:
                    # Use regex to get the cookie for cf_clearance=*;
                    cf_clearance_cookie = re.search(
                        "cf_clearance=.*?;",
                        message["params"]["headers"]["set-cookie"],
                    )
                    puid_cookie = re.search(
                        "_puid=.*?;",
                        message["params"]["headers"]["set-cookie"],
                    )
                    session_cookie = re.search(
                        "__Secure-next-auth.session-token=.*?;",
                        message["params"]["headers"]["set-cookie"],
                    )
                    if cf_clearance_cookie:
                        # remove the semicolon and 'cf_clearance=' from the string
                        raw_cf_cookie = cf_clearance_cookie.group(0)
                        self.cf_clearance = raw_cf_cookie.split("=")[1][:-1]
                        logger.info("识别到 cf_clearance.")
                        self.cf_cookie_found = True
                    if puid_cookie:
                        raw_puid_cookie = puid_cookie.group(0)
                        self.puid_cookie = raw_puid_cookie.split("=")[1][:-1]
                        logger.info("识别到 puid.")
                        self.puid_cookie_found = True
                    if session_cookie:
                        logger.info("识别到 Session Token.")
                        raw_session_cookie = session_cookie.group(0)
                        self.session_token = raw_session_cookie.split("=")[1][:-1]
                        self.session_cookie_found = True
    def __detect_user_agent(self, message):
        if "params" in message:
            if "headers" in message["params"]:
                if "user-agent" in message["params"]["headers"]:
                    # Use regex to get the cookie for cf_clearance=*;
                    user_agent = message["params"]["headers"]["user-agent"]
                    self.user_agent = user_agent
                    self.agent_found = True
                    logger.info("识别到 User-Agent.")
                if "sec-ch-ua" in message["params"]["headers"]:
                    sec_ch_ua = message["params"]["headers"]["sec-ch-ua"]
                    self.sec_ch_ua = sec_ch_ua
                    self.sec_ch_ua_found = True
                    logger.info("识别到 Sec-CH-UA.")
    
    def _set_auth_headers(self):
        self.authheaders = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            'sec-ch-ua': self.sec_ch_ua,
            "Connection": "close",
            "Referer": "https://chat.openai.com/chat",
            "Authorization": f"Bearer {self.access_token_auth}",
            "Cookie": f"cf_clearance={self.cf_clearance}; __Secure-next-auth.session-token={self.session_token}",
        }

        rep = requests.get("https://chat.openai.com/backend-api/models", headers=self.authheaders)
        logger.debug(rep.text)


'''
def json_contains_key(driver, key):
    try:
        data = json.loads(driver.page_source)
        return key in data
    except Exception:
        return False
class CustomSSLAdapter(HTTPAdapter):
    def __init__(self, ssl_options, **kwargs):
        self.ssl_options = ssl_options
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = CustomPoolManager(
            ssl_options=self.ssl_options,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs
        )
class CustomPoolManager(poolmanager.PoolManager):
    def __init__(self, ssl_options, *args, **kwargs):
        self.ssl_options = ssl_options
        super().__init__(*args, **kwargs)

    def _new_pool(self, scheme, host, port, request_context=None):
        if scheme == "https":
            if request_context is None:
                request_context = {}
            request_context["ssl_context"] = self.ssl_options
        return super()._new_pool(scheme, host, port, request_context)
'''