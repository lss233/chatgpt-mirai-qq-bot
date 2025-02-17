from im_http_legacy_adapter.adapter import HttpLegacyAdapter, HttpLegacyConfig

from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin

logger = get_logger("HTTP-Legacy-Adapter")


class HttpLegacyAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("http_legacy", HttpLegacyAdapter, HttpLegacyConfig)

    def on_start(self):
        pass

    def on_stop(self):
        pass
