import os

from im_wecom_adapter.adapter import WecomAdapter, WecomConfig

from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.web.app import WebServer

logger = get_logger("Wecom-Adapter")


class WecomAdapterPlugin(Plugin):
    web_server: WebServer
    
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("wecom", WecomAdapter, WecomConfig, "企业微信应用 / 微信公众号", "微信官方消息 API，需要服务器支持外部访问。")
        self.web_server.add_static_assets("/assets/icons/im/wecom.svg", os.path.join(os.path.dirname(__file__), "assets", "wecom.svg"))
        
    def on_start(self):
        pass

    def on_stop(self):
        pass
