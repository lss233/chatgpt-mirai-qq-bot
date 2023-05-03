from enum import Enum
from typing import Optional

from EdgeGPT import ConversationStyle

from framework.llm import LlmFactory

from framework.drawing import DrawingAIFactory, SDWebUI
from framework.llm import YiyanAdapter
from framework.llm import ChatGPTAPIAdapter
from framework.llm import ChatGPTWebAdapter
from framework.llm import ClaudeInSlackAdapter
from framework.llm import BardAdapter
from framework.llm import BingAdapter
from framework.llm import PoeAdapter
from framework.llm.quora.poe_web import BotType as PoeBotType
from framework.llm import ChatGLM6BAdapter
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
config.scan_prompts()
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
