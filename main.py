import asyncio
import os
import signal
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.events.event_bus import EventBus
from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from framework.ioc.container import DependencyContainer
from framework.llm.llm_manager import LLMManager
from framework.llm.llm_registry import LLMBackendRegistry
from framework.memory.memory_manager import MemoryManager
from framework.memory.scopes import MemberScope, GroupScope, GlobalScope
from framework.memory.composes import DefaultMemoryComposer, DefaultMemoryDecomposer
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.workflow.core.dispatch import WorkflowDispatcher
from framework.logger import get_logger
from framework.workflow.core.block import BlockRegistry
from framework.workflow.core.dispatch import DispatchRuleRegistry
from framework.workflow.core.workflow import WorkflowRegistry
from framework.workflow.implementations.blocks import register_system_blocks
from framework.workflow.implementations.workflows import register_system_workflows
from framework.web.app import WebServer

logger = get_logger("Entrypoint")

# 定义优雅退出异常
class GracefulExit(SystemExit):
    code = 1

# 注册信号处理函数
def _signal_handler(*args):
    logger.warning("Interrupt signal received. Stopping application...")
    raise GracefulExit()

def init_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    
    # 注册工作流注册表
    workflow_registry = WorkflowRegistry(container)
    register_system_workflows(workflow_registry)  # 注册系统工作流
    workflow_registry.load_workflows()  # 加载自定义工作流
    container.register(WorkflowRegistry, workflow_registry)
    
    # 注册调度规则注册表
    dispatch_registry = DispatchRuleRegistry(container)
    dispatch_registry.load_rules()  # 加载调度规则
    container.register(DispatchRuleRegistry, dispatch_registry)
    
    return container

def init_memory_system(container: DependencyContainer):
    """初始化记忆系统"""
    memory_manager = MemoryManager(container)
    
    # 注册默认作用域
    memory_manager.register_scope("member", MemberScope)
    memory_manager.register_scope("group", GroupScope)
    memory_manager.register_scope("global", GlobalScope)
    
    # 注册默认组合器和解析器
    memory_manager.register_composer("default", DefaultMemoryComposer)
    memory_manager.register_decomposer("default", DefaultMemoryDecomposer)
    
    container.register(MemoryManager, memory_manager)
    return memory_manager

def main():
    loop = asyncio.new_event_loop()
    
    logger.info("Starting application...")
    
    # 配置文件路径
    config_path = "config.yaml"

    # 加载配置文件
    logger.info(f"Loading configuration from {config_path}")
    if os.path.exists(config_path):
        config = ConfigLoader.load_config(config_path, GlobalConfig)
        logger.info("Configuration loaded successfully")
    else:
        logger.warning(f"Configuration file {config_path} not found, using default configuration")
        logger.warning("Please create a configuration file by copying config.yaml.example to config.yaml and modify it according to your needs")
        config = GlobalConfig()
    
    container = init_container()
    
    container.register(asyncio.AbstractEventLoop, loop)
    
    container.register(EventBus, EventBus())
    
    container.register(GlobalConfig, config)
    
    container.register(BlockRegistry, BlockRegistry())
    container.register(IMRegistry, IMRegistry())
    container.register(LLMBackendRegistry, LLMBackendRegistry())
    
    im_manager = IMManager(container)
    container.register(IMManager, im_manager)
    
    llm_manager = LLMManager(container)
    container.register(LLMManager, llm_manager)
    
    plugin_loader = PluginLoader(container, "plugins")
    container.register(PluginLoader, plugin_loader)
    
    workflow_dispatcher = WorkflowDispatcher(container)
    container.register(WorkflowDispatcher, workflow_dispatcher)

    # 初始化记忆系统
    logger.info("Initializing memory system...")
    memory_manager = init_memory_system(container)

    # 注册系统 blocks
    register_system_blocks(container.resolve(BlockRegistry))
    
    # 发现并加载内部插件
    logger.info("Discovering internal plugins...")
    plugin_loader.discover_internal_plugins()

    # 发现并加载外部插件
    logger.info("Discovering external plugins...")
    plugin_loader.discover_external_plugins()

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
    plugin_loader.start_plugins()

    # 初始化并启动Web服务器
    logger.info("Starting web server...")
    web_server = WebServer(container)
    container.register(WebServer, web_server)
    loop.run_until_complete(web_server.start())

    # 注册信号处理函数
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        # 保持程序运行
        logger.info("Application started. Waiting for events...")
        loop.run_forever()
    except GracefulExit:
        logger.info("Graceful exit requested")
    finally:
        # 关闭记忆系统
        logger.info("Shutting down memory system...")
        memory_manager.shutdown()
        
        # 停止Web服务器
        logger.info("Stopping web server...")
        loop.run_until_complete(web_server.stop())
        
        # 停止所有 adapter
        im_manager.stop_adapters(loop=loop)
        # 停止插件
        plugin_loader.stop_plugins()
        # 关闭事件循环
        loop.close()
        logger.info("Application stopped gracefully")

if __name__ == "__main__":
    main()