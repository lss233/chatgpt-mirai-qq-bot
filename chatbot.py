from revChatGPT.ChatGPT import Chatbot
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict, Tuple
from config import Config
from loguru import logger
import json
import os, sys
import asyncio
import uuid

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
    async def get_chat_response(self, message) -> Tuple[Dict[str, Any], Exception]:
        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id
        final_resp = None
        exception = None
        try:
            final_resp = bot.ask(message)
            self.conversation_id = final_resp["conversation_id"]
            self.parent_id = final_resp["parent_id"]
        except Exception as e:
            exception = e
        return final_resp, exception
sessions = {}


def get_chat_session(id: str) -> ChatSession:
    if id not in sessions:
        sessions[id] = ChatSession()
    return sessions[id]
