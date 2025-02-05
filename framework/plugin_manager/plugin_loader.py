import importlib
import os
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Type
import sys
import shutil
import subprocess

from framework.ioc.container import DependencyContainer
from framework.ioc.inject import Inject
from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from framework.plugin_manager.plugin_event_bus import PluginEventBus
from framework.plugin_manager.models import PluginInfo
from framework.plugin_manager.utils import get_package_metadata

class PluginLoader:
    def __init__(self, container: DependencyContainer, plugin_dir: str):
        self.plugins = []
        self.plugin_infos: Dict[str, PluginInfo] = {}  # 存储插件信息
        self.container = container
        self.logger = get_logger("PluginLoader")
        self._loaded_entry_points = set()  # 记录已加载的entry points
        self.plugin_dir = plugin_dir
        self.loaded_modules = {}
        self.internal_plugins = []

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

    async def install_plugin(self, package_name: str, version: Optional[str] = None) -> Optional[PluginInfo]:
        """安装插件"""
        try:
            # 构建安装命令
            cmd = [sys.executable, "-m", "pip", "install"]
            if version:
                cmd.append(f"{package_name}=={version}")
            else:
                cmd.append(package_name)
                
            # 执行安装
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Failed to install plugin: {stderr.decode()}")
                
            # 导入并加载插件
            module = importlib.import_module(package_name)
            plugin_info = self._load_plugin_info(module)
            if plugin_info:
                self.plugin_infos[plugin_info.package_name] = plugin_info
                return plugin_info
                
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
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", plugin_info.package_name]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Failed to uninstall plugin: {stderr.decode()}")
                
            # 清理插件信息
            if plugin_name in self.plugin_infos:
                del self.plugin_infos[plugin_name]
            if plugin_name in self.loaded_modules:
                del self.loaded_modules[plugin_name]
                
            return True
            
        except Exception as e:
            raise Exception(f"Failed to uninstall plugin: {str(e)}")
            
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否成功启用
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            raise ValueError(f"Plugin {plugin_name} not found")
            
        if plugin_info.is_enabled:
            return True
            
        try:
            # 加载插件
            if plugin_info.is_internal:
                plugin_class = self._load_internal_plugin(plugin_name)
            else:
                plugin_class = self._load_external_plugin(plugin_name)
                
            if not plugin_class:
                raise ValueError(f"Failed to load plugin class for {plugin_name}")
                
            # 实例化并初始化插件
            plugin = self.instantiate_plugin(plugin_class)
            plugin.on_load()
            plugin.on_start()
            
            # 更新状态
            self.plugins.append(plugin)
            plugin_info.is_enabled = True
            
            self.logger.info(f"Plugin {plugin_name} enabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable plugin {plugin_name}: {e}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否成功禁用
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            raise ValueError(f"Plugin {plugin_name} not found")
            
        if not plugin_info.is_enabled:
            return True
            
        try:
            # 找到并停止插件实例
            plugin = next((p for p in self.plugins if p.__class__.__name__ == plugin_name), None)
            if plugin:
                plugin.on_stop()
                self.plugins.remove(plugin)
            
            # 更新状态
            plugin_info.is_enabled = False
            
            self.logger.info(f"Plugin {plugin_name} disabled")
            return True
            
        except Exception as e:
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
            
            # 执行更新
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", plugin_info.package_name]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Failed to update plugin: {stderr.decode()}")
                
            # 重新加载插件
            if plugin_name in self.loaded_modules:
                module = self.loaded_modules[plugin_name]
                module = importlib.reload(module)
                self.loaded_modules[plugin_name] = module
                
            # 更新插件信息
            new_info = self._load_plugin_info(module)
            if new_info:
                self.plugin_infos[plugin_name] = new_info
                return new_info
                
        except Exception as e:
            raise Exception(f"Failed to update plugin: {str(e)}")
            
        return None
        
    def _load_plugin_info(self, module) -> Optional[PluginInfo]:
        """从模块加载插件信息"""
        try:
            if hasattr(module, '__plugin_info__'):
                return PluginInfo(**module.__plugin_info__)
        except Exception:
            pass
        return None
    
    def discover_external_plugins(self):
        """发现并加载所有已安装的外部插件"""
        eps = entry_points(group=Plugin.ENTRY_POINT_GROUP)
        
        for ep in eps:
            if ep.name not in self._loaded_entry_points:
                try:
                    self._load_external_plugin(ep.name)
                except Exception as e:
                    self.logger.error(f"Failed to load external plugin {ep.name}: {e}")