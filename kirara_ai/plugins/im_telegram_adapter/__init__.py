import asyncio
import os

from im_telegram_adapter.adapter import TelegramAdapter, TelegramConfig

from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.web.app import WebServer

logger = get_logger("TG-Adapter")


class TelegramAdapterPlugin(Plugin):
    web_server: WebServer
    
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register(
            "telegram",
            TelegramAdapter,
            TelegramConfig,
            "Telegram 机器人",
            "Telegram 官方机器人，支持私聊、群聊、 Markdown 格式消息。",
            """
Telegram 机器人,配置流程可参考 [Telegram 官方文档](https://core.telegram.org/bots/tutorial) 和 [Kirara AI 文档](https://kirara-docs.app.lss233.com/guide/configuration/im.html)。
            """
        )
        # 添加当前文件夹下的 assets/telegram.svg 文件夹到 web 服务器
        local_logo_path = os.path.join(os.path.dirname(__file__), "assets", "telegram.png")
        self.web_server.add_static_assets("/assets/icons/im/telegram.png", local_logo_path)

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
