from revChatGPT.revChatGPT import Chatbot
import json
with open("config.json", "r") as jsonfile:
    config_data = json.load(jsonfile)

class ChatSession:
    def __init__(self, conversation_id=None):
        self.chatbot = None
bots = {}

# Refer to https://github.com/acheong08/ChatGPT
def find_or_create_chatbot(id: str):
    if id in bots:
        return bots[id]
    else:
        print(f"Generating new chatbot session for id {id}")
        bot = Chatbot(config_data["openai"], conversation_id=None)
        bot.reset_chat()
        bots[id] = bot
        return bot