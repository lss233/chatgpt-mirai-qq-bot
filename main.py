from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.events.event_bus import EventBus
from framework.im.adapter_registry import AdapterRegistry
from framework.im.manager import IMManager
from framework.ioc.container import DependencyContainer
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher
from framework.logger import get_logger

def main():
    logger = get_logger("Entrypoint")
    
    logger.info("Starting application...")
    
    # 配置文件路径
    config_path = "config.yaml"

    # 加载配置文件
    logger.info(f"Loading configuration from {config_path}")
    config = ConfigLoader.load_config(config_path, GlobalConfig)
    logger.info("Configuration loaded successfully")
    
    container = DependencyContainer()
    logger.info("Dependency container created")
    
    logger.info("Registering EventBus in dependency container")
    container.register(EventBus, EventBus())
    
    logger.info("Registering GlobalConfig in dependency container")
    container.register(GlobalConfig, config)
    
    logger.info("Registering AdapterRegistry in dependency container")
    container.register(AdapterRegistry, AdapterRegistry())
    
    logger.info("Creating IMManager instance")
    manager = IMManager(container)
    container.register(IMManager, manager)
    
    logger.info("Creating PluginLoader instance")
    plugin_loader = PluginLoader(container)
    container.register(PluginLoader, plugin_loader)
    
    logger.info("Creating WorkflowDispatcher instance")
    workflow_dispatcher = WorkflowDispatcher()
    container.register(WorkflowDispatcher, workflow_dispatcher)
    
    # 发现并加载内部插件
    logger.info("Discovering plugins...")
    plugin_loader.discover_internal_plugins("plugins")

    # 初始化插件
    logger.info("Loading plugins")
    plugin_loader.load_plugins()
    
    # 创建 IM 生命周期管理器
    logger.info("Starting adapters")
    manager.start_adapters()
    
    # 启动插件
    logger.info("Starting plugins")
    plugin_loader.start_plugins()

    try:
        # 保持程序运行
        logger.info("Application started. Waiting for events...")
        while True:
            pass
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt detected. Stopping application...")
    
    # 停止所有 adapter
    logger.info("Stopping adapters")
    manager.stop_adapters()
    # 停止插件
    logger.info("Stopping plugins")
    plugin_loader.stop_plugins()
    logger.info("Application stopped gracefully")

if __name__ == "__main__":
    main()