from config import Config
from manager.bot import BotManager

config = Config.load_config()
botManager = BotManager(config.openai.accounts)

