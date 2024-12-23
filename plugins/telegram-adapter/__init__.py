from framework.im.telegram.adapter import TelegramAdapter
from framework.im.telegram.config import TelegramConfig
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin

logger = get_logger("TG-Adapter")
class ExamplePlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.adapter_registry.register("telegram", TelegramAdapter, TelegramConfig)
        logger.info("ExamplePlugin loaded")

    def on_start(self):
        logger.info("ExamplePlugin started")

    def on_stop(self):
        logger.info("ExamplePlugin stopped")
