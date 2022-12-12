from revChatGPT.revChatGPT import AsyncChatbot, generate_uuid
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict, Tuple
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