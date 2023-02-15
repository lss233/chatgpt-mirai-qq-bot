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
from manager import BotManager, BotInfo

config = Config.load_config()
botManager = BotManager(config.openai.accounts)

def setup():
    botManager.login()


class ChatSession:
    chatbot: BotInfo = None
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
        self.chatbot = botManager.pick()

    def rollback_conversation(self) -> bool:
        if len(self.prev_parent_id) <= 0:
            return False
        self.conversation_id = self.prev_conversation_id.pop()
        self.parent_id = self.prev_parent_id.pop()
        return True

    async def get_chat_response(self, message) -> str:
        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)

        bot = self.chatbot.bot
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, bot.ask, message)

        if self.chatbot.mode == 'proxy':
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
