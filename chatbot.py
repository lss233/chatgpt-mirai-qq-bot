from revChatGPT.ChatGPT import Chatbot
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from graia.ariadne.message import Source
from typing import Union, Any, Dict, Tuple
from config import Config
from loguru import logger
import os
import asyncio
import uuid

config = Config.load_config()
# Refer to https://github.com/acheong08/ChatGPT
try:
    logger.info("登录 OpenAI 中...")
    logger.info("请在新打开的浏览器窗口中完成验证。")
    if 'XPRA_PASSWORD' in os.environ:
        logger.info("如果您使用 xpra，请使用自己的浏览器访问 xpra 程序的端口，以访问到本程序启动的浏览器。")

    bot = Chatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None)
    logger.info("登录成功，保存登录信息中……")

    logger.debug(f"获取到 session_token {bot.config['session_token']}")

except Exception as e:
    logger.exception(e)

    if str(e) == "local variable 'driver' referenced before assignment":
        logger.error("无法启动，请检查是否安装了 chrome，或手动指定 chrome driver 的位置。")
    else:
        logger.error("OpenAI 登录失败，可能是 session_token 过期或无法通过 CloudFlare 验证，建议歇息一下再重试。")
    exit(-1)


class ChatSession:

    def __init__(self, app: Ariadne, target: Union[Friend, Group], source: Source):
        self.app = app
        self.target = target
        self.source = source

        self.timeout_task = None
        self.reset_conversation()

    def reset_conversation(self):
        self.__cancel_timeout_task()
        self.conversation_id = None
        self.parent_id = str(uuid.uuid4())
        self.prev_conversation_id = []
        self.prev_parent_id = []

    def rollback_conversation(self) -> bool:
        self.__cancel_timeout_task()
        if len(self.prev_parent_id) <= 0:
            return False
        self.conversation_id = self.prev_conversation_id.pop()
        self.parent_id = self.prev_parent_id.pop()
        return True

    def jump_to_conversation(self, conversation_id, parent_id):
        self.conversation_id = conversation_id
        self.parent_id = parent_id

    async def get_chat_response(self, message) -> str:
        self.__create_timeout_task()

        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id

        final_resp = None
        try:
            final_resp = bot.ask(message)
            self.conversation_id = final_resp["conversation_id"]
            self.parent_id = final_resp["parent_id"]
        finally:
            self.__cancel_timeout_task()
        return final_resp
    
    def __cancel_timeout_task(self):
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = None

    def __create_timeout_task(self):
        task = asyncio.create_task(self.__handle_timeout_task())
        self.timeout_task = task
    
    async def __handle_timeout_task(self):
        await asyncio.sleep(config.response.timeout)
        await self.app.send_message(self.target, config.response.timeout_format, quote=self.source if config.response.quote else False)


__sessions = {}


def get_chat_session(id: str, app: Ariadne, target: Union[Friend, Group], source: Source) -> Tuple[ChatSession, bool]:
    is_new_session = False
    if id not in __sessions:
        __sessions[id] = ChatSession(app, target, source)
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
