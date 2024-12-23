from abc import ABC, abstractmethod

from framework.im.adapter_registry import AdapterRegistry
from framework.im.manager import IMManager
from framework.ioc.inject import Inject
from framework.plugin_manager.plugin_event_bus import PluginEventBus
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher

class Plugin(ABC):
    event_bus: PluginEventBus
    workflow_dispatcher: WorkflowDispatcher
    adapter_registry: AdapterRegistry
    im_manager: IMManager    
    
    @abstractmethod
    def on_load(self):
        pass

    @abstractmethod
    def on_start(self):
        pass

    @abstractmethod
    def on_stop(self):
        pass