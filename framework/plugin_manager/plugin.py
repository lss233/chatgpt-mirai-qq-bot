from abc import ABC, abstractmethod

from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from framework.ioc.inject import Inject
from framework.llm.llm_registry import LLMBackendRegistry
from framework.plugin_manager.plugin_event_bus import PluginEventBus
from framework.workflow.core.dispatch import WorkflowDispatcher

class Plugin(ABC):
    """
    插件基类。
    外部插件需要在 setup.py 中注册 entry_points:
    
    setup(
        name='your-plugin-name',
        ...
        entry_points={
            'chatgpt_mirai.plugins': [
                'plugin_name = your_package.module:PluginClass'
            ]
        }
    )
    """
    
    ENTRY_POINT_GROUP = 'chatgpt_mirai.plugins'
    
    event_bus: PluginEventBus
    workflow_dispatcher: WorkflowDispatcher
    llm_registry: LLMBackendRegistry
    im_registry: IMRegistry
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