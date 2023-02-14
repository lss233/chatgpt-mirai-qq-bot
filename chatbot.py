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

    def __init__(self):
        self.reset_conversation()

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

    def jump_to_conversation(self, conversation_id, parent_id):
        self.conversation_id = conversation_id
        self.parent_id = parent_id

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


def get_chat_session(id: str) -> Tuple[ChatSession, bool]:
    is_new_session = False
    if id not in __sessions:
        __sessions[id] = ChatSession()
        is_new_session = True

    return __sessions[id], is_new_session

"""有些时候需要自动做出一些初始化行为，比如导入一些预设的人设，与此同时还可能要向目标用户发送类似于 '进度条' 的东西"""
async def initial_process(session: ChatSession):
    logger.debug("初始化处理中...")
    """
    例子：
    event = await session.app.send_message(session.target, '加载人设中...')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await session.app.send_message(session.target, '加载人设中(1/3)')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await session.app.send_message(session.target, '加载人设中(2/3)')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await session.app.send_message(session.target, '加载人设完毕')
    """

    """
    也许可以换成conv_id式初始化？无论如何先在这里留一个函数大概不会有错...
    """

    """
    conv_id = 'c56325ed-2ce6-443a-b66d-852afc12bc7d'
    pare_id = 'c18dd20-c42c-4145-8e86-9ac8efdf4f57'
    session.jump_to_conversation(conv_id, pare_id)
    """

"""有些时候还会希望用一些关键词来导入一些预设，与此同时还可能要向目标用户发送类似于 '进度条' 的东西"""
async def keyword_presets_process(session: ChatSession, message: str) -> Union[str, None]:
    """
    例子：
    keyword = message.strip()
    if keyword == '某个字符':
        event = await session.app.send_message(session.target, '猫娘加载中...')
        resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
        return '猫娘加载完毕'
    elif keyword == '某个字符2':
        event = await session.app.send_message(session.target, '猫娘加载中...')
        resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
        return '猫娘加载完毕'
    """

    """
    也许可以换成conv_id式初始化？无论如何先在这里留一个函数大概不会有错...
    """    
    return None
