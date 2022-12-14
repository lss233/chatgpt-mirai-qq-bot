from revChatGPT.revChatGPT import AsyncChatbot, generate_uuid
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict, Tuple
from config import Config
from loguru import logger
import json
import os, sys
import asyncio

with open("config.json", "rb") as f:
    guessed_json = from_bytes(f.read()).best()
    if not guessed_json:
        raise ValueError("无法识别 JSON 格式!")
    
    config = Config.parse_obj(json.loads(str(guessed_json)))
# Refer to https://github.com/acheong08/ChatGPT
try:
    logger.info("登录 OpenAI 中……")
    logger.info("请在新打开的浏览器窗口中完成验证")
    if 'XPRA_PASSWORD' in os.environ:
        logger.info("如果您使用 xpra，请使用自己的浏览器访问 xpra 程序的端口，以访问到本程序启动的浏览器。")
    
    bot = AsyncChatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None, base_url=config.openai.base_url)
    if not "cf_clearance" in bot.config:
        asyncio.run(bot.refresh_session())
    logger.info("登录成功，保存登录信息中……")

    if config.system.auto_save_cf_clearance:
        config.openai.cf_clearance = bot.config["cf_clearance"]
        config.openai.user_agent = bot.config["user_agent"]

    if config.system.auto_save_session_token:
        config.openai.session_token = bot.config["session_token"]
    
    logger.debug(f"获取到 cf_clearance {bot.config['cf_clearance']}")
    logger.debug(f"获取到 session_token {bot.config['session_token']}")
except Exception as e:
    logger.exception(e)
    logger.error("OpenAI 登录失败，可能是 session_token 过期或无法通过 CloudFlare 验证，建议歇息一下再重试。")
    exit(-1)

if config.system.auto_save_cf_clearance or config.system.auto_save_session_token:
    with open("config.json", "wb") as f:
        try:
            logger.debug(f"配置文件编码 {guessed_json.encoding} {config.response.timeout_format}")
            parsed_json = json.dumps(config.dict(), ensure_ascii=False, indent=4).encode(sys.getdefaultencoding())
            f.write(parsed_json)
        except Exception as e:
            logger.exception(e)
            logger.warning("配置保存失败")

class ChatSession:
    def __init__(self):
        self.reset_conversation()

    def reset_conversation(self):
        self.conversation_id = None
        self.parent_id = generate_uuid()
        self.prev_conversation_id = []
        self.prev_parent_id = []
    def rollback_conversation(self) -> bool:
        if len(self.prev_parent_id) <= 0:
            return False
        self.conversation_id = self.prev_conversation_id.pop()
        self.parent_id = self.prev_parent_id.pop()
        return True
    async def get_chat_response(self, message) -> Tuple[Dict[str, Any], Exception]:
        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id
        final_resp = None
        exception = None
        try:
            async for resp in await bot.get_chat_response(message, output="stream"):
                if final_resp is None:
                    logger.debug("已收到回应，正在接收中……")
                self.conversation_id = resp["conversation_id"]
                self.parent_id = resp["parent_id"]
                final_resp = resp
        except Exception as e:
            exception = e
        return final_resp, exception
sessions = {}


def get_chat_session(id: str) -> Tuple[ChatSession, bool]:
    is_new_session = False
    if id not in sessions:
        sessions[id] = ChatSession()
        is_new_session = True

    return sessions[id], is_new_session

"""有些时候需要自动做出一些初始化行为，比如导入一些预设的人设，与此同时还可能要向目标用户发送类似于 '进度条' 的东西"""
async def initial_process(app: Ariadne, target: Union[Friend, Group], session: ChatSession):
    """
    例子：
    event = await app.send_message(target, '加载人设中...')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await app.send_message(target, '加载人设中(1/3)')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await app.send_message(target, '加载人设中(2/3)')
    resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
    event = await app.send_message(target, '加载人设完毕')
    """
    pass

"""有些时候还会希望用一些关键词来导入一些预设，与此同时还可能要向目标用户发送类似于 '进度条' 的东西"""
async def keyword_presets_process(app: Ariadne, target: Union[Friend, Group], session: ChatSession, message: str) -> Union[str, None]:
    """
    例子：
    keyword = message.strip()
    if keyword == '某个字符':
        event = await app.send_message(target, '猫娘加载中...')
        resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
        return '猫娘加载完毕'
    elif keyword == '某个字符2':
        event = await app.send_message(target, '猫娘加载中...')
        resp = await session.get_chat_response('你是一只猫娘你是一只猫娘你是一只猫娘')
        return '猫娘加载完毕'
    """
    return None
