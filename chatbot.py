from revChatGPT.revChatGPT import AsyncChatbot, generate_uuid
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict, Tuple, Union
from config import Config
import json

with open("config.json", "rb") as f:
    guessed_json = from_bytes(f.read()).best()
    if not guessed_json:
        raise ValueError("无法识别 JSON 格式!")
    
    config = Config.parse_obj(json.loads(str(guessed_json)))

# Refer to https://github.com/acheong08/ChatGPT
bot = AsyncChatbot(config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None, base_url=config.openai.base_url)

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
