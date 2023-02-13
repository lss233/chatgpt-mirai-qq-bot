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
import json

config = Config.load_config()

os.environ.setdefault('TEMPERATURE', str(config.openai.temperature))

bot = None

def setup():
    global bot
    try:
        bot = Chatbot(email=config.openai.email, password=config.openai.password, proxy=config.openai.proxy, insecure=config.openai.insecure_auth, session_token=config.openai.session_token)
    except KeyError as e:
        if str(e) == 'accessToken':
            logger.error("无法获取 accessToken，请检查 session_token 是否过期")
        raise e

    try:
        logger.debug("Session token: " + bot.session_token)
    except:
        pass
class ChatSession:
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
        if len(bot.conversations.conversations[self.conversation_id].messages) == 0:
            return None
        return bot.conversations.conversations[self.conversation_id].messages[-1].text
    def reset_conversation(self):
        bot.conversations.conversations[self.conversation_id] = Conversation()
        if not self.preset == 'default':
            preset_conversations = config.load_preset(self.preset)
            self.base_prompt = preset_conversations[0]
            for message in preset_conversations[1:]:
                user, txt = message.split(':', maxsplit=2)
                bot.conversations.add_message(Message(txt, user), self.conversation_id)
        else:
            self.base_prompt = '你是 ChatGPT，一个大型语言模型。请以对话方式回复。\n\n\n'
    def rollback_conversation(self) -> bool:
        if not self.conversation_id in bot.conversations.conversations:
            return False
        bot.conversations.rollback(self.conversation_id, num = 2)
        
        last_message = self.get_last_message()
        if last_message is None:
            return ''
        
        return last_message

    async def get_chat_response(self, message) -> str:
        async with self.lock:
            os.environ.setdefault('BASE_PROMPT', self.base_prompt)
            result = ''
            async for data in bot.ask(prompt=message, conversation_id=self.conversation_id):
                result = result + data["choices"][0]["text"].replace("<|im_end|>", "")
            return result

__sessions = {}

def get_chat_session(id: str) -> ChatSession:
    if id not in __sessions:
        __sessions[id] = ChatSession(id)
    return __sessions[id]