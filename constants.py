from config import Config
from manager.bot import BotManager

config = Config.load_config()
config.scan_presets()

botManager = BotManager(config.openai.accounts)

