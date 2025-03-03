import asyncio
import os

from im_qqbot_adapter.adapter import QQBotAdapter, QQBotConfig

from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.web.app import WebServer

logger = get_logger("QQBot-Adapter")


class QQBotAdapterPlugin(Plugin):
    web_server: WebServer
    
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("qqbot", QQBotAdapter, QQBotConfig, "QQBot 机器人", "QQ 开放平台机器人，支持群聊、私聊和 QQ 频道。")
        # 添加当前文件夹下的 assets/telegram.svg 文件夹到 web 服务器
        local_logo_path = os.path.join(os.path.dirname(__file__), "assets", "qqbot.svg")
        self.web_server.add_static_assets("/assets/icons/im/qqbot.svg", local_logo_path)

    def on_start(self):
        pass

    def on_stop(self):
        try:
            tasks = []
            loop = asyncio.get_event_loop()
            for key, adapter in self.im_manager.get_adapters().items():
                if isinstance(adapter, QQBotAdapter) and adapter.is_running:
                    tasks.append(self.im_manager.stop_adapter(key, loop))
            for key in list(self.im_manager.get_adapters().keys()):
                self.im_manager.delete_adapter(key)
            loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:

            logger.error(f"Error stopping QQBot adapter: {e}")
        finally:
            self.im_registry.unregister("qqbot")
        logger.info("QQBot adapter stopped")
