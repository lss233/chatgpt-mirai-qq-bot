# -*- coding: utf-8 -*-
# @Time    : 12/31/22 3:51 PM
# @FileName: chatopenai.py
# @Software: PyCharm
# @Github    ：sudoskys
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
        raise ValueError("无法识别 JSON 格式")

    config = Config.parse_obj(json.loads(str(guessed_json)))

try:
    bot = Chatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None)
    logger.debug(f"获取 api key {bot.config['api_key']}")
    # 校验 Key 格式
    for it in bot.config['api_key']:
        it: str
        if not it.startswith("sk-"):
            raise Exception("配置了非法的 Api Key")

except Exception as e:
    logger.exception(e)
    exit(-1)


# TODO 迁移方法

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
