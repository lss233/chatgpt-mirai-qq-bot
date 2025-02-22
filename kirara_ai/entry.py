# For embedded python
import asyncio
import os
import signal

from kirara_ai.config.config_loader import ConfigLoader
from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.events.event_bus import EventBus
from kirara_ai.im.im_registry import IMRegistry
from kirara_ai.im.manager import IMManager
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.llm_manager import LLMManager
from kirara_ai.llm.llm_registry import LLMBackendRegistry
from kirara_ai.logger import get_logger
from kirara_ai.memory.composes import DefaultMemoryComposer, DefaultMemoryDecomposer
from kirara_ai.memory.memory_manager import MemoryManager
from kirara_ai.memory.scopes import GlobalScope, GroupScope, MemberScope
from kirara_ai.plugin_manager.plugin_loader import PluginLoader
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.block import BlockRegistry
from kirara_ai.workflow.core.dispatch import DispatchRuleRegistry, WorkflowDispatcher
from kirara_ai.workflow.core.workflow import WorkflowRegistry
from kirara_ai.workflow.implementations.blocks import register_system_blocks
from kirara_ai.workflow.implementations.workflows import register_system_workflows

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


def init_application() -> DependencyContainer:
    """初始化应用程序"""
    logger.info("Initializing application...")
    
    # 配置文件路径
    config_path = "config.yaml"

    # 加载配置文件
    logger.info(f"Loading configuration from {config_path}")
    if os.path.exists(config_path):
        config = ConfigLoader.load_config(config_path, GlobalConfig)
        logger.info("Configuration loaded successfully")
    else:
        logger.warning(
            f"Configuration file {config_path} not found, using default configuration"
        )
        logger.warning(
            "Please create a configuration file by copying config.yaml.example to config.yaml and modify it according to your needs"
        )
        config = GlobalConfig()

    container = init_container()
    container.register(asyncio.AbstractEventLoop, asyncio.new_event_loop())
    container.register(EventBus, EventBus())
    container.register(GlobalConfig, config)
    container.register(BlockRegistry, BlockRegistry())
    
    # 注册工作流注册表
    workflow_registry = WorkflowRegistry(container)
    container.register(WorkflowRegistry, workflow_registry)

    # 注册调度规则注册表
    dispatch_registry = DispatchRuleRegistry(container)
    container.register(DispatchRuleRegistry, dispatch_registry)

    container.register(IMRegistry, IMRegistry())
    container.register(LLMBackendRegistry, LLMBackendRegistry())

    im_manager = IMManager(container)
    container.register(IMManager, im_manager)

    llm_manager = LLMManager(container)
    container.register(LLMManager, llm_manager)
    plugin_loader = PluginLoader(container, os.path.join(os.path.dirname(__file__), "plugins"))
    container.register(PluginLoader, plugin_loader)

    workflow_dispatcher = WorkflowDispatcher(container)
    container.register(WorkflowDispatcher, workflow_dispatcher)
    
    container.register(WebServer, WebServer(container))

    # 初始化记忆系统
    logger.info("Initializing memory system...")
    init_memory_system(container)

    # 注册系统 blocks
    register_system_blocks(container.resolve(BlockRegistry))

    # 发现并加载插件
    plugin_loader = container.resolve(PluginLoader)
    logger.info("Discovering internal plugins...")
    plugin_loader.discover_internal_plugins()
    logger.info("Discovering external plugins...")
    plugin_loader.discover_external_plugins()
    logger.info("Loading plugins")
    plugin_loader.load_plugins()

    # 加载工作流和调度规则
    workflow_registry = container.resolve(WorkflowRegistry)
    workflow_registry.load_workflows()
    register_system_workflows(workflow_registry)
    dispatch_registry = container.resolve(DispatchRuleRegistry)
    dispatch_registry.load_rules()

    # 加载模型
    llm_manager = container.resolve(LLMManager)
    logger.info("Loading LLMs")
    llm_manager.load_config()

    return container

def run_application(container: DependencyContainer):
    """运行应用程序"""
    loop = container.resolve(asyncio.AbstractEventLoop)
        
    # 启动Web服务器
    logger.info("Starting web server...")
    web_server = container.resolve(WebServer)
    loop.run_until_complete(web_server.start())
    
    # 启动插件
    plugin_loader = container.resolve(PluginLoader)
    plugin_loader.start_plugins()
    
    # 启动适配器
    logger.info("Starting adapters")
    im_manager = container.resolve(IMManager)
    im_manager.start_adapters(loop=loop)
    
    # 注册信号处理函数
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    try:
        logger.success("Kirara AI 启动完毕，等待消息中...")
        logger.success(
            f"WebUI 管理平台本地访问地址：http://127.0.0.1:{web_server.config.web.port}/"
        )
        logger.success("Application started. Waiting for events...")
        loop.run_forever()
    except GracefulExit:
        logger.info("Graceful exit requested")
    finally:
        # 关闭记忆系统
        memory_manager = container.resolve(MemoryManager)
        logger.info("Shutting down memory system...")
        memory_manager.shutdown()

        # 停止Web服务器
        logger.info("Stopping web server...")

        # 停止所有 adapter
        im_manager.stop_adapters(loop=loop)
        # 停止插件
        plugin_loader.stop_plugins()
        # 停止Web服务器
        loop.run_until_complete(web_server.stop())
        # 关闭事件循环
        loop.close()
        logger.info("Application stopped gracefully")
