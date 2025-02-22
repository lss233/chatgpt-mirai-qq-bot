from im_wecom_adapter.adapter import WecomAdapter, WecomConfig

from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin

logger = get_logger("Wecom-Adapter")


class WecomAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("wecom", WecomAdapter, WecomConfig)

    def on_start(self):
        pass

    def on_stop(self):
        pass
