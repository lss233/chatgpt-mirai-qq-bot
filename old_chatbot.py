from typing import Tuple
from config import Config, OpenAIAuths
import asyncio
from manager.bot import BotManager, BotInfo
import atexit
from loguru import logger
import revChatGPT.V1 as V1

config = Config.load_config()
if type(config.openai) is OpenAIAuths:
    botManager = BotManager(config.openai.accounts)
else:
    # Backward-compatibility
    botManager = BotManager([config.openai])


def setup():
    if "browserless_endpoint" in config.openai.dict() and config.openai.browserless_endpoint is not None:
        V1.BASE_URL = config.openai.browserless_endpoint
    botManager.login()
    config.scan_presets()


class ChatSession:
    chatbot: BotInfo = None
    session_id: str

    def __init__(self, session_id):
        self.session_id = session_id
        self.prev_conversation_id = []
        self.prev_parent_id = []
        self.parent_id = None
        self.conversation_id = None
        self.chatbot = botManager.pick()

    async def load_conversation(self, keyword='default'):
        if keyword not in config.presets.keywords:
            if not keyword == 'default':
                raise ValueError("预设不存在，请检查你的输入是否有问题！")
        else:
            presets = config.load_preset(keyword)
            for text in presets:
                if text.startswith('#'):
                    continue
                elif text.startswith('ChatGPT:'):
                    yield text.split('ChatGPT:')[-1].strip()
                elif text.startswith('User:'):
                    await self.get_chat_response(text.split('User:')[-1].strip())
                else:
                    await self.get_chat_response(text.split('User:')[-1].strip())

    def reset_conversation(self):
        if self.chatbot and \
                self.chatbot.account.auto_remove_old_conversations and \
                self.conversation_id:
            self.chatbot.bot.delete_conversation(self.conversation_id)
        self.conversation_id = None
        self.parent_id = None
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
        resp = await loop.run_in_executor(None, self.chatbot.ask, message, self.conversation_id, self.parent_id)

        if self.conversation_id is None and self.chatbot.account.title_pattern:
            self.chatbot.bot.change_title(resp["conversation_id"],
                                          self.chatbot.account.title_pattern.format(session_id=self.session_id))

        self.conversation_id = resp["conversation_id"]
        self.parent_id = resp["parent_id"]

        return resp["message"]


__sessions = {}


def get_chat_session(session_id: str) -> Tuple[ChatSession, bool]:
    new_session = False
    if session_id not in __sessions:
        __sessions[session_id] = ChatSession(session_id)
        new_session = True
    return __sessions[session_id], new_session


def conversation_remover():
    logger.info("删除会话中……")
    for session in __sessions.values():
        if session.chatbot.account.auto_remove_old_conversations and session.chatbot and session.conversation_id:
            try:
                session.chatbot.bot.delete_conversation(session.conversation_id)
            except Exception as e:
                logger.error(f"删除会话 {session.conversation_id} 失败：{str(e)}")


atexit.register(conversation_remover)
