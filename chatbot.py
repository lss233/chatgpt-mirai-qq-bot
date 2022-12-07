from revChatGPT.revChatGPT import Chatbot
import json
with open("config.json", "r") as jsonfile:
    config_data = json.load(jsonfile)

# Refer to https://github.com/acheong08/ChatGPT
bot = Chatbot(config_data["openai"], conversation_id=None, debug=True)
class ChatSession:
    def __init__(self):
        self.reset_conversation()
    def reset_conversation(self):
        self.conversation_id = None
        self.parent_id = bot.generate_uuid()
    def apply(self, bot):
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id
sessions = {}


def get_chat_session(id: str):
    if id not in sessions:
        sessions[id] = ChatSession()
    return sessions[id]