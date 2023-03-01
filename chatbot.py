from typing import Tuple
from config import Config, OpenAIAuths
import asyncio
from manager.bot import BotManager, BotInfo
import atexit
from loguru import logger
import conversation_manager
import re
from tinydb import TinyDB, Query
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
    number: str

    def __init__(self, session_id):
        self.session_id = session_id
        self.number = session_id.split('-')[1]
        self.prev_conversation_id = None
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
        self.prev_conversation_id = None
        self.prev_parent_id = []
        self.chatbot = botManager.pick()

    def rollback_conversation(self) -> bool:
        if len(self.prev_parent_id) <= 0:
            return False
        # self.conversation_id = self.prev_conversation_id.pop()
        self.parent_id = self.prev_parent_id.pop()
        # 回滚一次对话
        conversation_manager.rollback_last_parent_id(self.number,
                                                     self.conversation_id)
        return True

    # 解析读取历史会话得到的字符串
    def extract_conversations(self, result):

        output = ""
        message_mapping = result['mapping']
        current_node_id = result['current_node']
        current_node = message_mapping[current_node_id]
        conversation = []

        while current_node['parent'] is not None:
            current_message = current_node['message']
            if current_message is not None:
                author_role = current_message['author']['role']
                message_content = current_message['content']['parts'][0]
                if author_role == 'user':
                    conversation.append("you:" + message_content)
                elif author_role == 'assistant':
                    conversation.append("bot:" + message_content)

            current_node_id = current_node['parent']
            current_node = message_mapping[current_node_id]

        for line in reversed(conversation):
            output += line + "\n"

        return output

    async def get_chat_response(self, message) -> str:

        self.prev_conversation_id = self.conversation_id
        self.prev_parent_id.append(self.parent_id)
        logger.info(f"当前id:{self.conversation_id}, 父节点id:{self.parent_id}")

        # 如果消息包含进入会话x命令，则进入会话x
        into_talk_search = re.search(config.trigger.goto_talk, message)
        if into_talk_search:
            conversation_parents = conversation_manager.get_last_parent_id(self.number, int(into_talk_search.group(1)))
            if conversation_parents:
                self.conversation_id = conversation_parents[0]
                self.parent_id = conversation_parents[1][-1]
                self.prev_conversation_id = conversation_parents[0]
                self.prev_parent_id = conversation_parents[1][0:-1]
                self.chatbot = botManager.pick_id(conversation_parents[2])
                return f"进入会话{into_talk_search.group(1)}成功！"
            else:
                return f"进入会话{into_talk_search.group(1)}失败！停留在当前会话"

        # 如果消息包含删除会话x命令，则删除对应会话
        delete_talk_search = re.search(config.trigger.delete_talk, message)
        if delete_talk_search:
            result = conversation_manager.delete_session_record(self.number, int(delete_talk_search.group(1)))
            if result == 2:  # 如果删除的恰巧是最后一个，也就是当前会话
                self.reset_conversation()
            if result:
                return f"删除会话{delete_talk_search.group(1)}成功！"
            else:
                return f"删除会话{delete_talk_search.group(1)}失败！会话不存在"

        # 如果消息包含读取会话x命令，则读取对应会话
        read_talk_search = re.search(config.trigger.read_talk, message)
        if read_talk_search:
            conversation_parents = conversation_manager.get_last_parent_id(self.number, int(read_talk_search.group(1)))
            if conversation_parents:
                chatbot_save = self.chatbot
                self.chatbot = botManager.pick_id(conversation_parents[2])
                result = self.chatbot.bot.get_msg_history(conversation_parents[0], encoding='utf-8')
                result = self.extract_conversations(result)
                self.chatbot = chatbot_save
                logger.info(
                    f"会话{read_talk_search.group(1)}的聊天记录如下：\n{result}")
                return f"读取会话成功！\n会话{read_talk_search.group(1)}的聊天记录如下：\n{result}"
            else:
                return f"读取会话{read_talk_search.group(1)}失败！停留在当前会话"

        # 如果消息包含清空会话命令（config.trigger.rollback_command所定义的内容），则清空会话
        if message.strip() in config.trigger.clear_talk_command:
            self.reset_conversation()
            if conversation_manager.clear_user_sessions(self.number):
                return "清空会话成功！"
            else:
                return "清空会话失败！你是不是还没对话过。"

        # 如果消息包含 会话名：*** 命令，则删除对应会话
        rename_talk_search = re.search(config.trigger.rename_talk, message)
        if rename_talk_search:
            if self.conversation_id:
                conversation_manager.update_session(self.number, self.conversation_id, rename_talk_search.group(1))
                self.chatbot.bot.change_title(self.conversation_id, (
                            self.session_id.encode('unicode-escape') + rename_talk_search.group(1).encode(
                        'unicode-escape')).decode('utf-8'))
                return f"会话名已改为{rename_talk_search.group(1)}"
            else:
                return "会话还没开始，不能设置会话名！"

        bot = self.chatbot.bot
        botManager.update_bot_time(self.chatbot.id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id
        logger.info(
            f"当前id:{self.conversation_id}, 父节点id:{self.parent_id}")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, self.chatbot.ask, message, self.conversation_id, self.parent_id)

        flag = False
        if self.conversation_id is None:
            flag = True

        self.conversation_id = resp["conversation_id"]
        self.parent_id = resp["parent_id"]

        # 添加对话记录
        conversation_manager.add_session_record(self.number, self.conversation_id, message[:20],
                                                self.chatbot.account_id,
                                                self.parent_id)

        if flag:
            self.chatbot.bot.change_title(self.conversation_id, f"{self.session_id}{message[:20].encode('utf-8')}")
        # self.chatbot.bot.change_title(resp["conversation_id"],self.chatbot.account.title_pattern.format(session_id=f"{self.session_id}"+str(message[:20].encode("utf-8"))))##########################

        logger.info(
            f"当前id:{self.conversation_id}, 父节点id:{self.parent_id}")

        return resp["message"]


__sessions = {}


def get_chat_session(session_id: str) -> Tuple[ChatSession, bool]:
    number = session_id.split('-')[1]
    new_session = False

    if number not in __sessions:  #有可能是重启容器了（读取旧聊天最后一个），也有可能是新的用户（创建新聊天）

        # 创建一个新的聊天会话
        __sessions[number] = ChatSession(session_id)

        # 创建一个新的聊天会话
        __sessions[number] = ChatSession(session_id)

        # 打开数据库
        db = TinyDB('data/session_records.json')

        # 获取数据表
        table = db.table('session_records')

        # 读取数据
        session_records = table.all()
        if len(session_records) > 0:
            session_records = session_records[0]
        else:
            session_records = {}

        # 读取session_records字典
        # with open('session_records.json', 'r') as f:
        #     session_records = json.loads(f.read())
        if number in session_records:  #重启容器了
            if len(session_records[number]["sessions"]) > 0:
                __sessions[number].conversation_id = session_records[number]["sessions"][-1]["conversation_id"]
                __sessions[number].parent_id = session_records[number]["sessions"][-1]["parent_ids"][-1]
                __sessions[number].prev_conversation_id = session_records[number]["sessions"][-1]["conversation_id"]
                __sessions[number].prev_parent_id = session_records[number]["sessions"][-1]["parent_ids"][0:-1]
                __sessions[number].chatbot = botManager.pick_id(session_records[number]["sessions"][-1]["account_id"])
        else:  # 新用户开始聊天
            new_session = True

    return __sessions[number], new_session


def conversation_remover():
    logger.info("删除会话中……")
    for session in __sessions.values():
        if session.chatbot.account.auto_remove_old_conversations and session.chatbot and session.conversation_id:
            try:
                session.chatbot.bot.delete_conversation(session.conversation_id)
            except Exception as e:
                logger.error(f"删除会话 {session.conversation_id} 失败：{str(e)}")


atexit.register(conversation_remover)
