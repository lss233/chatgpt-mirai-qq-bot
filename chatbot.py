from revChatGPT.V2 import Chatbot, Message, Conversation
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
import json

config = Config.load_config()
botManager = BotManager(config.openai.accounts)

os.environ.setdefault('TEMPERATURE', str(config.openai.temperature))

def setup():
    botManager.login()

class ChatSession:
    chatbot: BotInfo = None
    chat_history: list[str]
    conversation_id: str
    preset: str
    base_prompt: str
    lock: asyncio.Lock

    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.load_conversation()
        self.lock = asyncio.Lock()

    def load_conversation(self, keyword='default'):
        if not keyword in config.presets.keywords:
            if not keyword == 'default':
                raise ValueError("预设不存在，请检查你的输入是否有问题！")
        self.preset = keyword
        
        self.reset_conversation()

        last_message = self.get_last_message()
        if last_message is None:
            return config.presets.loaded_successful
        else:
            return last_message
    def get_last_message(self):
        if len(self.chatbot.bot.conversations.conversations[self.conversation_id].messages) == 0:
            return None
        return self.chatbot.bot.conversations.conversations[self.conversation_id].messages[-1].text
    def reset_conversation(self):
        self.chatbot = botManager.pick()
        self.chatbot.conversations.conversations[self.conversation_id] = Conversation()
        if not self.preset == 'default':
            preset_conversations = config.load_preset(self.preset)
            self.base_prompt = preset_conversations[0]
            for message in preset_conversations[1:]:
                user, txt = message.split(':', maxsplit=2)
                self.chatbot.conversations.add_message(Message(txt, user), self.conversation_id)
        else:
            self.base_prompt = '你是 ChatGPT，一个大型语言模型。请以对话方式回复。\n\n\n'
        
    def rollback_conversation(self) -> bool:
        if not self.conversation_id in self.chatbot.conversations.conversations:
            return False
        self.chatbot.conversations.rollback(self.conversation_id, num = 2)
        
        last_message = self.get_last_message()
        if last_message is None:
            return ''
        
        return last_message

    async def get_chat_response(self, message) -> str:
        async with self.lock:
            os.environ.setdefault('BASE_PROMPT', self.base_prompt)
            result = ''
            async for data in self.chatbot.ask(prompt=message, conversation_id=self.conversation_id):
                result = result + data["choices"][0]["text"].replace("<|im_end|>", "")
            return result

__sessions = {}

def get_chat_session(id: str) -> ChatSession:
    if id not in __sessions:
        __sessions[id] = ChatSession(id)
    return __sessions[id]
