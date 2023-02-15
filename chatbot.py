from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from graia.ariadne.message import Source
from typing import Union, Any, Dict, Tuple
from config import Config
from loguru import logger
import os
import asyncio
import uuid
from time import sleep
from selenium.common.exceptions import TimeoutException

config = Config.load_config()
bot = None

def setup():
    global bot
    try:
        logger.info("登录 OpenAI 中...")
        if config.openai.mode == 'proxy':
            logger.info("当前模式：第三方代理")
            from revChatGPT.V1 import Chatbot
            bot = Chatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None)
        else:
            from revChatGPT.Unofficial import Chatbot
            logger.info("当前模式：浏览器直接访问")
            logger.info("这需要你拥有最新版的 Chrome 浏览器。")
            logger.info("即将打开浏览器窗口……")
            logger.info("提示：如果你看见了 Cloudflare 验证码，请手动完成验证。")
            logger.info("如果浏览器反复弹出，请阅读项目 FAQ。")

            if 'XPRA_PASSWORD' in os.environ:
                logger.info("如果您使用 xpra，请使用自己的浏览器访问 xpra 程序的端口，以访问到本程序启动的浏览器。")
            bot = Chatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None)
    except Exception as e:
        logger.exception(e)
        if config.openai.mode == 'proxy':
            if str(e) == 'Wrong status code':
                logger.error("OpenAI 登录失败，可能是账号密码有误。")
            else:
                logger.error("OpenAI 登录失败，可能是账号密码有误、需要设置本地正向代理或其他原因。")
        else:
            if str(e) == "local variable 'driver' referenced before assignment":
                logger.error("无法启动，请检查是否安装了 Chrome，或手动指定 Chromedriver 的位置")
                logger.error("参考资料：https://github.com/acheong08/ChatGPT/wiki/Setup#dependencies")
            elif e is TimeoutException:
                logger.error("等待超时：没有在规定时间内完成登录。")
            else:
                logger.error("OpenAI 登录失败，可能是 session_token 过期或无法通过 CloudFlare 验证，建议歇息一下再重试。")
                logger.error("你也可以将模式修改为第三方代理来绕过这个步骤。")
        raise e


class ChatSession:
    chat_history: list[str]
    def __init__(self):
        self.load_conversation()

    def load_conversation(self, keyword='default'):
        if not keyword in config.presets.keywords:
            if keyword == 'default':
                self.__default_chat_history = []
            else:
                raise ValueError("预设不存在，请检查你的输入是否有问题！")
        else:
            self.__default_chat_history = config.load_preset(keyword)
        self.reset_conversation()
        if len(self.chat_history) > 0:
            return self.chat_history[-1].split('\nChatGPT:')[-1].strip().rstrip("<|im_end|>")
        else:
            return config.presets.loaded_successful

    def reset_conversation(self):
        self.conversation_id = None
        self.parent_id = str(uuid.uuid4())
        self.prev_conversation_id = []
        self.prev_parent_id = []

    def rollback_conversation(self) -> bool:
        if len(self.prev_parent_id) <= 0:
            return False
        self.conversation_id = self.prev_conversation_id.pop()
        self.parent_id = self.prev_parent_id.pop()
        return True

    async def get_chat_response(self, message) -> str:
        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, bot.ask, message)

        if config.openai.mode == 'proxy':
            final_resp = None
            for item in resp:
                final_resp = item
            self.conversation_id = final_resp["conversation_id"]
            self.parent_id = final_resp["parent_id"]
            return final_resp["message"]
        else:
            self.conversation_id = resp["conversation_id"]
            self.parent_id = resp["parent_id"]
            return resp["message"]

__sessions = {}

def get_chat_session(id: str) -> ChatSession:
    if id not in __sessions:
        __sessions[id] = ChatSession()
    return __sessions[id]
