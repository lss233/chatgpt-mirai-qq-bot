from im_telegram_adapter.adapter import TelegramAdapter, TelegramConfig
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin

logger = get_logger("TG-Adapter")
class TelegramAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("telegram", TelegramAdapter, TelegramConfig)

    def on_start(self):
        pass
    def on_stop(self):
        pass