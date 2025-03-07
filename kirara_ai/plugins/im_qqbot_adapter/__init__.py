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
        self.im_registry.register(
            "qqbot", 
            QQBotAdapter, 
            QQBotConfig, 
            "QQ 开放平台机器人", 
            "QQ 官方机器人，需要服务器支持接收 QQ 的 Webhook 请求，支持基本的聊天功能，但不支持分段回复，群聊中需要被 @ 触发。",
            """
QQ 开放平台机器人，需要服务器支持接收 QQ 的 Webhook 请求，配置流程可参考 [QQ 开放平台文档](https://q.qq.com/wiki/) 和 [Kirara AI 文档](https://kirara-docs.app.lss233.com/guide/configuration/im.html)。
            """
        )
        local_logo_path = os.path.join(os.path.dirname(__file__), "assets", "qqbot.png")
        self.web_server.add_static_assets("/assets/icons/im/qqbot.png", local_logo_path)

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
