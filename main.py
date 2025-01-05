import asyncio
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.events.event_bus import EventBus
from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from framework.ioc.container import DependencyContainer
from framework.llm.llm_manager import LLMManager
from framework.llm.llm_registry import LLMBackendRegistry
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher
from framework.logger import get_logger

def main():
    loop = asyncio.new_event_loop()
    logger = get_logger("Entrypoint")
    
    logger.info("Starting application...")
    
    # 配置文件路径
    config_path = "config.yaml"

    # 加载配置文件
    logger.info(f"Loading configuration from {config_path}")
    config = ConfigLoader.load_config(config_path, GlobalConfig)
    logger.info("Configuration loaded successfully")
    
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    
    container.register(asyncio.AbstractEventLoop, loop)
    
    container.register(EventBus, EventBus())
    
    container.register(GlobalConfig, config)
    
    container.register(IMRegistry, IMRegistry())
    container.register(LLMBackendRegistry, LLMBackendRegistry())
    
    im_manager = IMManager(container)
    container.register(IMManager, im_manager)
    
    llm_manager = LLMManager(container)
    container.register(LLMManager, llm_manager)
    
    plugin_loader = PluginLoader(container)
    container.register(PluginLoader, plugin_loader)
    
    workflow_dispatcher = WorkflowDispatcher()
    container.register(WorkflowDispatcher, workflow_dispatcher)
    
    # 发现并加载内部插件
    logger.info("Discovering plugins...")
    plugin_loader.discover_internal_plugins("plugins")

    # 初始化插件
    logger.info("Loading plugins")
    plugin_loader.load_plugins()
    
    # 加载模型后端配置
    logger.info("Loading LLMs")
    llm_manager.load_config()
    
    # 创建 IM 生命周期管理器
    logger.info("Starting adapters")
    im_manager.start_adapters(loop=loop)
    
    # 启动插件
    logger.info("Starting plugins")
    plugin_loader.start_plugins()

    try:
        # 保持程序运行
        logger.info("Application started. Waiting for events...")
        while True:
            loop.run_forever()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt detected. Stopping application...")
    
    # 停止所有 adapter
    logger.info("Stopping adapters")
    im_manager.stop_adapters(loop=loop)
    # 停止插件
    logger.info("Stopping plugins")
    plugin_loader.stop_plugins()
    logger.info("Application stopped gracefully")

if __name__ == "__main__":
    main()