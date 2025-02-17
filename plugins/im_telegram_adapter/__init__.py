import asyncio

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
        try:
            tasks = []
            loop = asyncio.get_event_loop()
            for key, adapter in self.im_manager.get_adapters().items():
                if isinstance(adapter, TelegramAdapter) and adapter.is_running:
                    tasks.append(self.im_manager.stop_adapter(key, loop))
            for key in list(self.im_manager.get_adapters().keys()):
                self.im_manager.delete_adapter(key)
            loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:

            logger.error(f"Error stopping Telegram adapter: {e}")
        finally:
            self.im_registry.unregister("telegram")
        logger.info("Telegram adapter stopped")
