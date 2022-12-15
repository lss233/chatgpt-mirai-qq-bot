from revChatGPT.revChatGPT import AsyncChatbot, generate_uuid
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from graia.ariadne.message import Source
from typing import Any, Dict, Tuple, Union
from config import Config
from loguru import logger
import os
import asyncio

config = Config.load_config()
# Refer to https://github.com/acheong08/ChatGPT
try:
    logger.info("登录 OpenAI 中...")
    logger.info("请在新打开的浏览器窗口中完成验证。")
    if 'XPRA_PASSWORD' in os.environ:
        logger.info("如果您使用 xpra，请使用自己的浏览器访问 xpra 程序的端口，以访问到本程序启动的浏览器。")

    bot = AsyncChatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None, base_url=config.openai.base_url)
    if not "cf_clearance" in bot.config:
        asyncio.run(bot.refresh_session())

    logger.info("登录成功，保存登录信息中...")

    if config.system.auto_save_cf_clearance:
        config.openai.cf_clearance = bot.config["cf_clearance"]
        config.openai.user_agent = bot.config["user_agent"]

    if config.system.auto_save_session_token:
        config.openai.session_token = bot.config["session_token"]
    
    logger.debug(f"获取到 cf_clearance {bot.config['cf_clearance']}")
    logger.debug(f"获取到 session_token {bot.config['session_token']}")

    if config.system.auto_save_cf_clearance or config.system.auto_save_session_token:
        Config.save_config(config)

except Exception as e:
    logger.exception(e)
    logger.error("OpenAI 登录失败，可能是 session_token 过期或无法通过 CloudFlare 验证，建议稍后重试。")
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
        self.parent_id = generate_uuid()
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

    async def get_chat_response(self, message) -> Tuple[Dict[str, Any], Exception]:
        self.__create_timeout_task()

        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id

        final_resp = None
        exception = None
        try:
            async for resp in await bot.get_chat_response(message, output="stream"):
                if final_resp is None:
                    self.__cancel_timeout_task()
                    logger.debug("已收到回应，正在接收中...")
                
                self.conversation_id = resp["conversation_id"]
                self.parent_id = resp["parent_id"]
                final_resp = resp
        except Exception as e:
            self.__cancel_timeout_task()
            exception = e

        return final_resp, exception
    
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
async def initial_process(session: ChatSession) -> Exception:
    exception = None
    try:
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
        conv_id = '6909b2b7-2793-455b-af64-144d32195c6c'
        pare_id = '883c2057-9d0f-4889-9483-69cfee20d03b'
        session.jump_to_conversation(conv_id, pare_id)
    except Exception as e:
        exception = e

    return exception

"""有些时候还会希望用一些关键词来导入一些预设，与此同时还可能要向目标用户发送类似于 '进度条' 的东西"""
async def keyword_presets_process(session: ChatSession, message: str) -> Tuple[Union[str, None], Exception]:
    exception = None
    try:
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
    except Exception as e:
        exception = e
    
    return None, exception
