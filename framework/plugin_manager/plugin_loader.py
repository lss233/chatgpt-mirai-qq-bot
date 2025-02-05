import importlib
import os
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Type

from framework.ioc.container import DependencyContainer
from framework.ioc.inject import Inject
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from framework.plugin_manager.plugin_event_bus import PluginEventBus
from framework.plugin_manager.models import PluginInfo
from framework.plugin_manager.utils import get_package_metadata

class PluginLoader:
    def __init__(self, container: DependencyContainer):
        self.plugins = []
        self.plugin_infos: Dict[str, PluginInfo] = {}  # 存储插件信息
        self.container = container
        self.logger = get_logger("PluginLoader")
        self._loaded_entry_points = set()  # 记录已加载的entry points

    def register_plugin(self, plugin_class: Type[Plugin], plugin_name: str = None):
        """注册一个插件类，主要用于测试"""
        plugin = self.instantiate_plugin(plugin_class)
        self.plugins.append(plugin)
        
        # 创建并存储插件信息
        plugin_info = PluginInfo(
            name=plugin_class.__name__,
            package_name=plugin_name,
            description=plugin_class.__doc__ or '',
            version='1.0.0',
            author='Test',
            is_internal=True,
            is_enabled=True,
            metadata=getattr(plugin, 'metadata', None)
        )
        key = plugin_name or plugin_class.__name__
        self.plugin_infos[key] = plugin_info
        self.logger.info(f"Registered test plugin: {key}")
        return plugin

    def discover_internal_plugins(self, plugin_dir):
        """Discovers and loads internal plugins from a specified directory.

        Scans the given directory for subdirectories and attempts to load each as a plugin.

        Args:
            plugin_dir (str): Path to the directory containing plugin subdirectories.
        """
        self.logger.info(f"Discovering internal plugins from directory: {plugin_dir}")
        importlib.sys.path.append(plugin_dir)

        for plugin_name in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_path):
                self.logger.debug(f"Found plugin directory: {plugin_name}")
                self.load_plugin(plugin_name)

    def load_plugin(self, plugin_name: str):
        """加载插件，支持内部插件和外部插件"""
        self.logger.info(f"Loading plugin: {plugin_name}")
        try:
            if plugin_name.startswith('plugins.'):  # 内部插件
                self._load_internal_plugin(plugin_name)
            else:  # 外部插件
                self._load_external_plugin(plugin_name)
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def _load_internal_plugin(self, plugin_name: str):
        """加载内部插件"""
        module = importlib.import_module(plugin_name)
        plugin_classes = [
            cls for cls in module.__dict__.values() 
            if isinstance(cls, type) and issubclass(cls, Plugin) and cls != Plugin
        ]
        if not plugin_classes:
            raise ValueError(f"No valid plugin class found in module {plugin_name}")
        plugin_class = plugin_classes[0]
        plugin = self.instantiate_plugin(plugin_class)
        self.plugins.append(plugin)
        
        # 创建并存储插件信息
        plugin_info = PluginInfo(
            name=plugin_class.__name__,
            description=plugin_class.__doc__ or '',
            version='1.0.0',
            author='Internal',
            is_internal=True,
            is_enabled=True,
            metadata=getattr(plugin, 'metadata', None)
        )
        self.plugin_infos[plugin_name] = plugin_info
        self.logger.info(f"Internal plugin {plugin_name} loaded successfully")

    def _load_external_plugin(self, plugin_name: str):
        """加载外部插件"""
        eps = entry_points(group=Plugin.ENTRY_POINT_GROUP)
        for entry_point in eps:
            if entry_point.name == plugin_name or entry_point.module_name == plugin_name:
                if entry_point.name in self._loaded_entry_points:
                    self.logger.warning(f"Plugin {plugin_name} is already loaded")
                    return
                    
                plugin_class = entry_point.load()
                if not issubclass(plugin_class, Plugin):
                    raise ValueError(f"Plugin class must inherit from Plugin base class")
                    
                plugin = self.instantiate_plugin(plugin_class)
                self.plugins.append(plugin)
                self._loaded_entry_points.add(entry_point.name)
                
                # 获取并存储插件信息
                metadata = get_package_metadata(plugin_name)
                if metadata:
                    plugin_info = PluginInfo(
                        name=metadata['name'],
                        package_name=plugin_name,
                        description=metadata['description'],
                        version=metadata['version'],
                        author=metadata['author'],
                        is_internal=False,
                        is_enabled=True,
                        metadata=None
                    )
                    self.plugin_infos[plugin_name] = plugin_info
                
                self.logger.info(f"External plugin {plugin_name} loaded successfully")
                return
                
        raise ValueError(f"No plugin found with name {plugin_name}")

    def instantiate_plugin(self, plugin_class):
        """Instantiates a plugin class using dependency injection."""
        self.logger.debug(f"Instantiating plugin class: {plugin_class.__name__}")
        with self.container.scoped() as scoped_container:
            scoped_container.register(PluginEventBus, PluginEventBus())
            return Inject(scoped_container).create(plugin_class)()

    def load_plugins(self):
        """Initializes all loaded plugins."""
        self.logger.info("Initializing plugins...")
        for plugin in self.plugins:
            try:
                plugin.on_load()
                self.logger.info(f"Plugin {plugin.__class__.__name__} initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize plugin {plugin.__class__.__name__}: {e}")

    def start_plugins(self):
        """Starts all loaded plugins."""
        self.logger.info("Starting plugins...")
        for plugin in self.plugins:
            try:
                plugin.on_start()
                self.logger.info(f"Plugin {plugin.__class__.__name__} started")
            except Exception as e:
                self.logger.error(f"Failed to start plugin {plugin.__class__.__name__}: {e}")

    def stop_plugins(self):
        """Stops all loaded plugins."""
        self.logger.info("Stopping plugins...")
        for plugin in self.plugins:
            try:
                plugin.on_stop()
                plugin.event_bus.unregister_all()
                self.logger.info(f"Plugin {plugin.__class__.__name__} stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop plugin {plugin.__class__.__name__}: {e}")

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugin_infos.get(plugin_name)

    def get_all_plugin_infos(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return list(self.plugin_infos.values())