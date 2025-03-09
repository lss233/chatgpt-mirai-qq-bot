
from kirara_ai.plugin_manager.plugin import Plugin


class PluginEvent:
    def __init__(self, plugin: Plugin):
        self.plugin = plugin
        
    def __repr__(self):
        return f"{self.__class__.__name__}(plugin={self.plugin})"

class PluginStarted(PluginEvent):
    pass

class PluginStopped(PluginEvent):
    pass

class PluginLoaded(PluginEvent):
    pass