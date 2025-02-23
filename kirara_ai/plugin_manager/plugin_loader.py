import importlib
import os
import subprocess
import sys
from typing import Dict, List, Optional, Type

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.ioc.inject import Inject
from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.models import PluginInfo
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.plugin_manager.plugin_event_bus import PluginEventBus


class PluginLoader:
    def __init__(self, container: DependencyContainer, plugin_dir: str):
        self.plugins: Dict[str, Plugin] = {}  # 存储插件实例
        self.plugin_infos: Dict[str, PluginInfo] = {}  # 存储插件信息
        self.container = container
        self.logger = get_logger("PluginLoader")
        self._loaded_entry_points = set()  # 记录已加载的entry points
        self.plugin_dir = plugin_dir
        self.internal_plugins = []
        self.config = self.container.resolve(GlobalConfig)

    def register_plugin(self, plugin_class: Type[Plugin], plugin_name: str = None):
        """注册一个插件类，主要用于测试"""
        plugin = self.instantiate_plugin(plugin_class)
        key = plugin_name or plugin_class.__name__
        self.plugins[key] = plugin

        # 创建并存储插件信息
        plugin_info = PluginInfo(
            name=plugin_class.__name__,
            package_name=plugin_name,
            description=plugin_class.__doc__ or "",
            version="1.0.0",
            author="Test",
            is_internal=True,
            is_enabled=True,
            metadata=getattr(plugin, "metadata", None),
        )
        self.plugin_infos[key] = plugin_info
        self.logger.info(f"Registered test plugin: {key}")
        return plugin

    def discover_internal_plugins(self, plugin_dir=None):
        """Discovers and loads internal plugins from a specified directory.

        Scans the given directory for subdirectories and attempts to load each as a plugin.

        Args:
            plugin_dir (str): Path to the directory containing plugin subdirectories.
        """
        if not plugin_dir:
            plugin_dir = self.plugin_dir
        self.logger.info(f"Discovering internal plugins from directory: {plugin_dir}")
        importlib.sys.path.append(plugin_dir)

        for plugin_name in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_path):
                self.internal_plugins.append(plugin_name)
                self.logger.debug(f"Found plugin directory: {plugin_name}")
                self.load_plugin(plugin_name)

    def load_plugin(self, plugin_name: str):
        """加载插件，支持内部插件和外部插件"""
        self.logger.info(f"Loading plugin: {plugin_name}")
        try:
            if plugin_name in self.internal_plugins:  # 内部插件
                self._load_internal_plugin(plugin_name)
            else:  # 外部插件
                self._load_external_plugin(plugin_name)
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def _load_internal_plugin(self, plugin_name: str):
        """加载内部插件"""
        module = importlib.import_module(plugin_name)
        plugin_classes = [
            cls
            for cls in module.__dict__.values()
            if isinstance(cls, type) and issubclass(cls, Plugin) and cls != Plugin
        ]
        if not plugin_classes:
            raise ValueError(f"No valid plugin class found in module {plugin_name}")
        plugin_class = plugin_classes[0]
        plugin = self.instantiate_plugin(plugin_class)
        self.plugins[plugin_name] = plugin

        # 创建并存储插件信息
        plugin_info = PluginInfo(
            name=plugin_class.__name__,
            description=plugin_class.__doc__ or "",
            version="1.0.0",
            author="Internal",
            is_internal=True,
            is_enabled=True,
            metadata=getattr(plugin, "metadata", None),
        )
        self.plugin_infos[plugin_name] = plugin_info
        self.logger.info(f"Internal plugin {plugin_name} loaded successfully")
        return plugin

    def _load_external_plugin(self, plugin_name: str):
        """加载外部插件"""
        from importlib.metadata import entry_points

        # 获取插件的 entry point
        eps = entry_points(group=Plugin.ENTRY_POINT_GROUP)
        plugin_ep = next((ep for ep in eps if ep.name == plugin_name), None)

        if not plugin_ep:
            raise ValueError(f"Unable to find entry point for plugin {plugin_name}")

        try:
            # 加载插件类
            plugin_class = plugin_ep.load()

            # 检查插件类是否继承自 Plugin
            if not issubclass(plugin_class, Plugin):
                raise TypeError(
                    f"Plugin {plugin_name} must inherit from the Plugin class"
                )

            # 实例化插件并启动
            plugin: Plugin = self.instantiate_plugin(plugin_class)
            self.plugins[plugin_name] = plugin

            self.logger.info(f"Successfully loaded external plugin: {plugin_name}")
            return plugin
        except Exception as e:
            self.logger.error(f"Failed to load external plugin {plugin_name}: {e}")
            raise

    def instantiate_plugin(self, plugin_class):
        """Instantiates a plugin class using dependency injection."""
        self.logger.debug(f"Instantiating plugin class: {plugin_class.__name__}")
        with self.container.scoped() as scoped_container:
            scoped_container.register(PluginEventBus, PluginEventBus())
            return Inject(scoped_container).create(plugin_class)()

    def load_plugins(self):
        """Initializes all loaded plugins."""
        self.logger.info("Initializing plugins...")
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.on_load()
                self.logger.info(f"Plugin {plugin.__class__.__name__} initialized")
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize plugin {plugin.__class__.__name__}: {e}"
                )

    def start_plugins(self):
        """Starts all loaded plugins."""
        self.logger.info("Starting plugins...")
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.on_start()
                self.logger.info(f"Plugin {plugin.__class__.__name__} started")
            except Exception as e:
                self.logger.error(
                    f"Failed to start plugin {plugin.__class__.__name__}: {e}"
                )

    def stop_plugins(self):
        """Stops all loaded plugins."""
        self.logger.info("Stopping plugins...")
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.on_stop()
                plugin.event_bus.unregister_all()
                self.logger.info(f"Plugin {plugin.__class__.__name__} stopped")
            except Exception as e:
                self.logger.error(
                    f"Failed to stop plugin {plugin.__class__.__name__}: {e}"
                )

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugin_infos.get(plugin_name)

    def get_all_plugin_infos(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return list(self.plugin_infos.values())

    async def install_plugin(
        self, package_name: str, version: Optional[str] = None
    ) -> Optional[PluginInfo]:
        """安装插件"""
        try:
            # 构建安装命令
            cmd = [sys.executable, "-m", "pip", "install", "--index-url", self.config.update.pypi_registry]
            if version:
                cmd.append(f"{package_name}=={version}")
            else:
                cmd.append(package_name)

            # 执行安装
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            self.logger.info(f"Install plugin {package_name} output: {stdout.decode()}")
            if process.returncode != 0:
                raise Exception(f"Failed to install plugin: {stderr.decode()}")

            # 导入并加载插件
            self.discover_external_plugins()
            possible_plugin_infos = [
                info
                for info in self.plugin_infos.values()
                if info.package_name == package_name
            ]
            if possible_plugin_infos:
                return possible_plugin_infos[0]

        except Exception as e:
            raise Exception(f"Failed to install plugin: {str(e)}")

        return None

    async def uninstall_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            plugin_info = self.plugin_infos.get(plugin_name)
            if not plugin_info:
                return False

            if plugin_info.is_internal:
                raise Exception("Cannot uninstall internal plugin")

            # 卸载前先禁用插件
            await self.disable_plugin(plugin_name)

            # 执行卸载
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "uninstall",
                "-y",
                plugin_info.package_name,
            ]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            self.logger.info(
                f"Uninstall plugin {plugin_info.package_name} output: {stdout.decode()}"
            )

            if process.returncode != 0:
                raise Exception(f"Failed to uninstall plugin: {stderr.decode()}")

            # 清理插件信息
            if plugin_name in self.plugin_infos:
                del self.plugin_infos[plugin_name]

            return True

        except Exception as e:
            raise Exception(f"Failed to uninstall plugin: {str(e)}")

    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            raise ValueError(f"Plugin {plugin_name} not found")

        if plugin_info.is_enabled:
            return True

        try:
            # 加载插件
            if plugin_info.is_internal:
                plugin = self._load_internal_plugin(plugin_name)
            else:
                plugin = self._load_external_plugin(plugin_name)

            # 更新配置
            if plugin_name not in self.config.plugins.enable:
                self.config.plugins.enable.append(plugin_name)

            plugin.on_load()

            plugin.on_start()

            plugin_info.is_enabled = True

            self.logger.info(f"Plugin {plugin_name} enabled")
            return True

        except Exception as e:
            plugin_info.requires_restart = True
            self.logger.error(f"Failed to enable plugin {plugin_name}: {e}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            raise ValueError(f"Plugin {plugin_name} not found")

        if not plugin_info.is_enabled:
            return True

        try:
            # 找到并停止插件实例
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                print(isinstance(plugin, Plugin))
                plugin.on_stop()
                del self.plugins[plugin_name]

            # 更新配置
            if plugin_name in self.config.plugins.enable:
                self.config.plugins.enable.remove(plugin_name)

            plugin_info.is_enabled = False
            self.plugin_infos[plugin_name] = plugin_info

            self.logger.info(f"Plugin {plugin_name} disabled")
            return True

        except Exception as e:
            plugin_info.requires_restart = True
            self.logger.error(f"Failed to disable plugin {plugin_name}: {e}")
            return False

    async def update_plugin(self, plugin_name: str) -> Optional[PluginInfo]:
        """更新插件"""
        try:
            plugin_info = self.plugin_infos.get(plugin_name)
            if not plugin_info:
                return None

            if plugin_info.is_internal:
                raise Exception("Cannot update internal plugin")

            # 获取当前版本
            old_version = plugin_info.version
            # 先关闭插件
            await self.disable_plugin(plugin_name)
            # 执行更新
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--index-url",
                self.config.update.pypi_registry,
                plugin_info.package_name,
            ]

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            self.logger.info(
                f"Update plugin {plugin_info.package_name} output: {stdout.decode()}"
            )
            if process.returncode != 0:
                raise Exception(f"Failed to update plugin: {stderr.decode()}")

            self.discover_external_plugins()
            possible_plugin_infos = [
                info
                for info in self.plugin_infos.values()
                if info.package_name == plugin_info.package_name
            ]
            if possible_plugin_infos:
                if possible_plugin_infos[0].version != old_version:
                    return possible_plugin_infos[0]
                else:
                    raise Exception(
                        f"Failed to update plugin: {plugin_info.package_name} is already up to date"
                    )

        except Exception as e:
            raise Exception(f"Failed to update plugin: {str(e)}")

        return None

    def discover_external_plugins(self):
        """发现并加载所有已安装的外部插件"""
        self.logger.info("Discovering external plugins...")

        from importlib.metadata import distributions

        # 获取所有已安装的包
        for dist in distributions():
            try:
                # 检查包是否包含我们需要的 entry point
                eps = dist.entry_points
                plugin_eps = [ep for ep in eps if ep.group == Plugin.ENTRY_POINT_GROUP]

                if not plugin_eps:
                    continue

                for ep in plugin_eps:
                    try:
                        # 获取插件元数据
                        metadata = {
                            "name": dist.metadata["Name"],
                            "description": dist.metadata.get("Summary", ""),
                            "version": dist.metadata.get("Version", "1.0.0"),
                            "author": dist.metadata.get("Author", "Unknown"),
                        }

                        # 创建插件信息
                        plugin_info = PluginInfo(
                            name=ep.name,
                            package_name=dist.metadata["Name"],
                            description=metadata["description"],
                            version=metadata["version"],
                            author=metadata["author"],
                            is_internal=False,
                            is_enabled=ep.name in self.config.plugins.enable,
                            metadata=None,
                        )

                        # 存储插件信息
                        self.plugin_infos[ep.name] = plugin_info

                        # 如果插件在启用列表中，则加载它
                        if ep.name in self.config.plugins.enable:
                            self._load_external_plugin(ep.name)

                    except Exception as e:
                        self.logger.error(
                            f"Error processing metadata for plugin {ep.name}: {e}"
                        )

            except Exception as e:
                self.logger.error(
                    f"Error processing package {dist.metadata['Name']}: {e}"
                )
