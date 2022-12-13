from revChatGPT.revChatGPT import AsyncChatbot, generate_uuid
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict
from config import Config
from loguru import logger
import json
with open("config.json", "rb") as f:
    guessed_json = from_bytes(f.read()).best()
    if not guessed_json:
        raise ValueError("无法识别 JSON 格式!")
    
    config = Config.parse_obj(json.loads(str(guessed_json)))

# Refer to https://github.com/acheong08/ChatGPT
try:
    logger.info("登录 OpenAI 中……")
    logger.info("请在新打开的浏览器窗口中完成 Cloudflare 验证")
    bot = AsyncChatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None, base_url=config.openai.base_url)
except Exception as e:
    logger.exception(e)
    logger.error("OpenAI 登录失败，可能是 session_token 过期或无法通过 Cloudflare 验证，建议歇息一下再重试。")
    exit(-1)

class ChatSession:
    def __init__(self):
        self.reset_conversation()
    def reset_conversation(self):
        self.conversation_id = None
        self.parent_id = generate_uuid()
        self.prev_conversation_id = None
        self.prev_parent_id = None
    def rollback_conversation(self) -> bool:
        if self.prev_parent_id is None:
            return False
        self.conversation_id = self.prev_conversation_id
        self.parent_id = self.prev_parent_id
        self.prev_conversation_id = None
        self.prev_parent_id = None
        return True
    def get_chat_response(self, message, output="text") -> Awaitable[Dict[str, Any]]:
        try:
            self.prev_conversation_id = self.conversation_id
            self.prev_parent_id = self.parent_id
            bot.conversation_id = self.conversation_id
            bot.parent_id = self.parent_id
            return bot.get_chat_response(message, output=output, conversation_id=self.conversation_id, parent_id=self.parent_id)
        finally:
            self.conversation_id = bot.conversation_id
            self.parent_id = bot.parent_id
sessions = {}


def get_chat_session(id: str) -> ChatSession:
    if id not in sessions:
        sessions[id] = ChatSession()
    return sessions[id]
