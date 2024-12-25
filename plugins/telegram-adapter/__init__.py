from framework.im.telegram.adapter import TelegramAdapter
from framework.im.telegram.config import TelegramConfig
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin

logger = get_logger("TG-Adapter")
class TelegramAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("telegram", TelegramAdapter, TelegramConfig)
        logger.info("TelegramAdapterPlugin loaded")

    def on_start(self):
        logger.info("TelegramAdapterPlugin started")

    def on_stop(self):
        logger.info("TelegramAdapterPlugin stopped")
