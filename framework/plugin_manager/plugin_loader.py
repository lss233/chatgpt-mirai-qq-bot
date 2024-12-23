import importlib
import os

from framework.ioc.container import DependencyContainer
from framework.ioc.inject import Inject
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from framework.plugin_manager.plugin_event_bus import PluginEventBus

class PluginLoader:
    def __init__(self, container: DependencyContainer):
        self.plugins = []
        self.container = container
        self.logger = get_logger("PluginLoader")  # 使用 loguru 的 logger

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

    def load_plugin(self, plugin_name):
        """Dynamically loads a plugin module and instantiates its plugin class.

        Attempts to import the specified plugin module and create an instance of its plugin class.

        Args:
            plugin_name (str): Name of the plugin module to load.

        Raises:
            ImportError: If the plugin module cannot be imported.
            AttributeError: If no valid plugin class is found in the module.
        """
        self.logger.info(f"Loading plugin: {plugin_name}")
        try:
            module = importlib.import_module(plugin_name)
            plugin_classes = [cls for cls in module.__dict__.values() if isinstance(cls, type) and issubclass(cls, Plugin) and cls != Plugin]
            if not plugin_classes:
                raise ValueError(f"No valid plugin class found in module {plugin_name}")
            plugin_class = plugin_classes[0]
            plugin = self.instantiate_plugin(plugin_class)
            self.plugins.append(plugin)
            self.logger.info(f"Plugin {plugin_name} loaded successfully")
        except (ImportError, AttributeError, ValueError) as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def instantiate_plugin(self, plugin_class):
        """Instantiates a plugin class using dependency injection."""
        self.logger.debug(f"Instantiating plugin class: {plugin_class.__name__}")
        with self.container.scoped() as scoped_container:
            scoped_container.register(PluginEventBus, PluginEventBus())
            return Inject(scoped_container)(plugin_class)()

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