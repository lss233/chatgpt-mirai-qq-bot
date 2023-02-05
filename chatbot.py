from revChatGPT.Official import Chatbot, Prompt
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
import json

config = Config.load_config()
if 'api_key' not in config.openai:
    logger.error("请在 openai 中填写 api_key。")
    exit(-1)
bot = Chatbot(api_key=config.openai.api_key)

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
        self.chat_history = self.__default_chat_history.copy()

    def rollback_conversation(self) -> bool:
        if len(self.chat_history) < 1:
            return False
        self.chat_history.pop()
        if len(self.chat_history)  == 0:
            return ''
        else:
            return self.chat_history[-1].split('\nChatGPT:')[-1].strip().rstrip("<|im_end|>")

    async def get_chat_response(self, message) -> str:
        bot.prompt.chat_history = self.chat_history
        loop = asyncio.get_event_loop()
        final_resp = await loop.run_in_executor(None, bot.ask, message)
        final_resp = final_resp["choices"][0]["text"]
        return final_resp

__sessions = {}

def get_chat_session(id: str) -> ChatSession:
    if id not in __sessions:
        __sessions[id] = ChatSession()
    return __sessions[id]