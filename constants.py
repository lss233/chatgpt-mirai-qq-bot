from enum import Enum
from typing import Optional

from EdgeGPT import ConversationStyle

from framework.llm import LlmFactory
from framework.accounts import account_manager
from framework.drawing import DrawingAIFactory, SDWebUI
from framework.llm.baidu.yiyan import YiyanAdapter
from framework.llm.openai.api import ChatGPTAPIAdapter
from framework.llm.openai.web import ChatGPTWebAdapter
from framework.llm.claude.slack import ClaudeInSlackAdapter
from framework.llm.google.bard import BardAdapter
from framework.llm.microsoft.bing import BingAdapter
from framework.llm.quora.poe_web import PoeAdapter, BotType as PoeBotType
from framework.llm.thudm.chatglm_6b import ChatGLM6BAdapter
from config import Config

LlmFactory.register("chatgpt-web", ChatGPTWebAdapter, ())
LlmFactory.register("chatgpt-api", ChatGPTAPIAdapter, ())
LlmFactory.register("yiyan", YiyanAdapter, ())
LlmFactory.register("slack-claude", ClaudeInSlackAdapter, ())
LlmFactory.register("bard", BardAdapter, ())
LlmFactory.register("bing-c", BingAdapter, (ConversationStyle.creative,))
LlmFactory.register("bing-p", BingAdapter, (ConversationStyle.precise,))
LlmFactory.register("bing-b", BingAdapter, (ConversationStyle.balanced,))
LlmFactory.register("chatglm-api", ChatGLM6BAdapter, ())
LlmFactory.register("poe-capybara", PoeAdapter, (PoeBotType.Sage, ))
LlmFactory.register("poe-beaver", PoeAdapter, (PoeBotType.GPT4, ))
LlmFactory.register("poe-a2_2", PoeAdapter, (PoeBotType.Claude2, ))
LlmFactory.register("poe-a2", PoeAdapter, (PoeBotType.Claude, ))
LlmFactory.register("poe-claude", PoeAdapter, (PoeBotType.Claude, ))
LlmFactory.register("poe-chinchilla", PoeAdapter, (PoeBotType.ChatGPT, ))
LlmFactory.register("poe-chatgpt", PoeAdapter, (PoeBotType.ChatGPT, ))
LlmFactory.register("poe-nutria", PoeAdapter, (PoeBotType.Dragonfly, ))


# TODO: DrawingAIFactory.register_ai("yiyan", YiyanAdapter, ("drawing", ))

config = Config.load_config()
config.scan_presets()
# config: Optional[Config] = None
proxy: Optional[str] = config.check_proxy()
# botManager = BotManager(config)

if config.sdwebui:
    DrawingAIFactory.register("sd", SDWebUI, (config.sdwebui, ))
DrawingAIFactory.register("bing", BingAdapter, ("drawing", ConversationStyle.creative))
DrawingAIFactory.register("openai", ChatGPTAPIAdapter, ("drawing",))

class BotPlatform(Enum):
    AriadneBot = "mirai"
    DiscordBot = "discord"
    Onebot = "onebot"
    TelegramBot = "telegram"
    HttpService = "http"
    WecomBot = "wecom"
