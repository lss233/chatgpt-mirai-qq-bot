from enum import Enum

from config import Config
from manager.bot import BotManager

config = Config.load_config()
config.scan_presets()

botManager = BotManager(config)


class LlmName(Enum):
    SlackClaude = "slack-claude"
    PoeSage = "poe-sage"
    PoeGPT4 = "poe-gpt4"
    PoeClaude2 = "poe-claude2"
    PoeClaude = "poe-claude"
    PoeClaude100k = "poe-claude100k"
    PoeChatGPT = "poe-chatgpt"
    PoeDragonfly = "poe-dragonfly"
    PoeNeevaAI = "poe-neevaai"
    ChatGPT_Web = "chatgpt-web"
    ChatGPT_Api = "chatgpt-api"
    Bing = "bing"
    BingC = "bing-c"
    BingB = "bing-b"
    BingP = "bing-p"
    Bard = "bard"
    YiYan = "yiyan"
    ChatGLM = "chatglm-api"


class BotPlatform(Enum):
    AriadneBot = "mirai"
    DiscordBot = "discord"
    Onebot = "onebot"
    TelegramBot = "telegram"
    HttpService = "http"
    WecomBot = "wecom"
