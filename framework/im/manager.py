import asyncio
from typing import Dict

from framework.config.global_config import GlobalConfig
from framework.im.im_registry import IMRegistry
from framework.ioc.container import DependencyContainer
from framework.ioc.inject import Inject
from framework.logger import get_logger

logger = get_logger("IMManager")
class IMManager:
    """
    IM 生命周期管理器，负责管理所有 adapter 的启动、运行和停止。
    """
    container: DependencyContainer
    
    config: GlobalConfig
    
    im_registry: IMRegistry
    
    @Inject()
    def __init__(self, container: DependencyContainer, config: GlobalConfig, adapter_registry: IMRegistry):
        self.container = container
        self.config = config
        self.im_registry = adapter_registry
        self.adapters: Dict[str, any] = {}


    def start_adapters(self, loop=None):
        """
        根据配置文件中的 enable_ims 启动对应的 adapter。
        :param loop: 负责执行的 event loop
        """
        if loop is None:
            loop = asyncio.get_event_loop()
            
        enable_ims = self.config.ims.enable
        credentials = self.config.ims.configs

        for platform, adapter_keys in enable_ims.items():
            # 动态获取 adapter 类
            adapter_class = self.im_registry.get(platform)
            # 动态获取 adapter 的配置类
            config_class = self.im_registry.get_config_class(platform)
            tasks = []
            for key in adapter_keys:
                # 从 credentials 中读取配置
                if key not in credentials:
                    raise ValueError(f"Credential for key '{key}' is missing in credentials.")
                credential = credentials[key]

                # 动态实例化 adapter 的配置对象
                adapter_config = config_class(**credential)

                # 创建 adapter 实例
                with self.container.scoped() as scoped_container:
                    scoped_container.register(config_class, adapter_config)
                    adapter = Inject(scoped_container).create(adapter_class)()
                self.adapters[key] = adapter
                tasks.append(asyncio.ensure_future(self._start_adapter(key, adapter, loop), loop=loop))
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

    def stop_adapters(self, loop=None):
        """
        停止所有已启动的 adapter。
        :param loop: 负责执行的 event loop
        """
        if loop is None:
            loop = asyncio.get_event_loop()
            
        for key, adapter in self.adapters.items():
            loop.run_until_complete(self._stop_adapter(key, adapter, loop))
            

    def get_adapters(self) -> Dict[str, any]:
        """
        获取所有已启动的 adapter。
        :return: 已启动的 adapter 字典。
        """
        return self.adapters
    
    async def _start_adapter(self, key, adapter, loop):
        logger.info(f"Starting adapter: {key}")
        await adapter.start()
        logger.info(f"Started adapter: {key}")

    async def _stop_adapter(self, key, adapter, loop):
        logger.info(f"Stopping adapter: {key}")
        await adapter.stop()
        logger.info(f"Stopped adapter: {key}")