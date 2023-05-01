from enum import Enum
from typing import Optional

from config import Config

# config = Config.load_config()
# config.scan_presets()
config: Optional[Config] = None

# botManager = BotManager(config)


class LlmName(Enum):
    SlackClaude = "slack-claude"
    PoeSage = "poe-sage"
    PoeGPT4 = "poe-gpt4"
    PoeClaude2 = "poe-claude2"
    PoeClaude = "poe-claude"
    PoeChatGPT = "poe-chatgpt"
    PoeDragonfly = "poe-dragonfly"
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
