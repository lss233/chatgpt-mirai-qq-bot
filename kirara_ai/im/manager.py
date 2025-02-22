import asyncio
from typing import Dict, Type

from kirara_ai.config.config_loader import pydantic_validation_wrapper
from kirara_ai.config.global_config import GlobalConfig, IMConfig
from kirara_ai.im.adapter import IMAdapter
from kirara_ai.im.im_registry import IMRegistry
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.ioc.inject import Inject
from kirara_ai.logger import get_logger

logger = get_logger("IMManager")


class IMManager:
    """
    IM 生命周期管理器，负责管理所有 adapter 的启动、运行和停止。
    """

    container: DependencyContainer

    config: GlobalConfig

    im_registry: IMRegistry

    @Inject()
    def __init__(
        self,
        container: DependencyContainer,
        config: GlobalConfig,
        adapter_registry: IMRegistry,
    ):
        self.container = container
        self.config = config
        self.im_registry = adapter_registry
        self.adapters: Dict[str, IMAdapter] = {}

    def get_adapter_type(self, name: str) -> str:
        """
        获取指定名称的 adapter 类型。
        :param name: adapter 的名称
        :return: adapter 的类型
        """
        return self.get_adapter_config(name).adapter

    def has_adapter(self, name: str) -> bool:
        """
        检查指定名称的 adapter 是否存在。
        :param name: adapter 的名称
        :return: 如果 adapter 存在返回 True，否则返回 False
        """
        return name in self.adapters

    def get_adapter_config(self, name: str) -> IMConfig:
        """
        获取指定名称的 adapter 的配置。
        :param name: adapter 的名称
        :return: adapter 的配置
        """
        for im in self.config.ims:
            if im.name == name:
                return im
        raise ValueError(f"Adapter {name} not found")

    def update_adapter_config(self, name: str, config: IMConfig):
        """
        更新指定名称的 adapter 的配置。
        :param name: adapter 的名称
        :param config: adapter 的配置
        """
        self.get_adapter_config(name).config = config.model_dump()

    def delete_adapter(self, name: str):
        """
        删除指定名称的 adapter。
        :param name: adapter 的名称
        """
        self.adapters.pop(name, None)
        self.config.ims = [im for im in self.config.ims if im.name != name]

    @pydantic_validation_wrapper
    def start_adapters(self, loop=None):
        """
        根据配置文件中的 enable_ims 启动对应的 adapter。
        :param loop: 负责执行的 event loop
        """
        if loop is None:
            loop = asyncio.new_event_loop()
        tasks = []
        for im in self.config.ims:
            try:
                # 动态获取 adapter 类
                adapter_class = self.im_registry.get(im.adapter)
                # 动态获取 adapter 的配置类
                config_class = self.im_registry.get_config_class(im.adapter)
                # 动态实例化 adapter 的配置对象
                adapter_config = config_class(**im.config)

                # 创建 adapter 实例
                adapter = self.create_adapter(im.name, adapter_class, adapter_config)
                if im.enable:
                    tasks.append(
                        asyncio.ensure_future(
                            self._start_adapter(im.name, adapter), loop=loop
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to start adapter {im.name}: {e}")
                continue
        if len(tasks) > 0:
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        else:
            logger.warning("No adapters to start, please check your config")

    def stop_adapters(self, loop=None):
        """
        停止所有已启动的 adapter。
        :param loop: 负责执行的 event loop
        """
        if loop is None:
            loop = asyncio.get_event_loop()

        for key, adapter in self.adapters.items():
            loop.run_until_complete(self._stop_adapter(key, adapter))

    def get_adapters(self) -> Dict[str, IMAdapter]:
        """
        获取所有已启动的 adapter。
        :return: 已启动的 adapter 字典。
        """
        return self.adapters

    def get_adapter(self, key: str) -> IMAdapter:
        """
        获取指定 key 的 adapter。
        :param key: adapter 的 key
        :return: 指定 key 的 adapter
        """
        return self.adapters[key]

    async def _start_adapter(self, key: str, adapter: IMAdapter):
        logger.info(f"Starting adapter: {key}")
        await adapter.start()
        adapter.is_running = True
        logger.info(f"Started adapter: {key}")

    async def _stop_adapter(self, key: str, adapter: IMAdapter):
        logger.info(f"Stopping adapter: {key}")
        await adapter.stop()
        adapter.is_running = False
        logger.info(f"Stopped adapter: {key}")

    def stop_adapter(self, adapter_id: str, loop: asyncio.AbstractEventLoop):
        if adapter_id not in self.adapters:
            raise ValueError(f"Adapter {adapter_id} not found")
        adapter = self.adapters[adapter_id]
        return asyncio.ensure_future(self._stop_adapter(adapter_id, adapter), loop=loop)

    def start_adapter(self, adapter_id: str, loop: asyncio.AbstractEventLoop):
        if adapter_id not in self.adapters:
            raise ValueError(f"Adapter {adapter_id} not found")
        adapter = self.adapters[adapter_id]
        return asyncio.ensure_future(
            self._start_adapter(adapter_id, adapter), loop=loop
        )

    def is_adapter_running(self, key: str) -> bool:
        """
        检查指定 key 的 adapter 是否正在运行。
        :param key: adapter 的 key
        :return: 如果 adapter 正在运行返回 True，否则返回 False
        """

        return key in self.adapters and getattr(self.adapters[key], "is_running", False)

    def create_adapter(
        self, name: str, adapter_class: Type[IMAdapter], adapter_config: IMConfig
    ) -> IMAdapter:
        with self.container.scoped() as scoped_container:
            scoped_container.register(adapter_config.__class__, adapter_config)
            adapter = Inject(scoped_container).create(adapter_class)()
            adapter.is_running = False
        self.adapters[name] = adapter
        return adapter
