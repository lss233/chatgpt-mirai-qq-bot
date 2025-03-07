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
        self.im_registry.register(
            "wecom",
            WecomAdapter,
            WecomConfig,
            "企业微信应用 / 微信公众号",
            "微信官方消息 API，需要服务器支持接收微信的 Webhook 访问。",
            r"""
企业微信应用/微信公众号官方消息 API，需要服务器支持 Webhook 访问。详情配置可参考[微信官方文档](https://open.work.weixin.qq.com/wwopen/manual/detail?t=selfBuildApp)和[Kirara配置文档](https://kirara-docs.app.lss233.com/guide/configuration/im.html#%E4%BC%81%E4%B8%9A%E5%BE%AE%E4%BF%A1-wecom)。
            """
        )
        self.web_server.add_static_assets(
            "/assets/icons/im/wecom.png", os.path.join(os.path.dirname(__file__), "assets", "wecom.png")
        )
    def on_start(self):
        pass

    def on_stop(self):
        pass
