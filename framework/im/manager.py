from typing import Dict

from framework.config.global_config import GlobalConfig
from framework.im.adapter_registry import AdapterRegistry
from framework.ioc.inject import Inject

class IMManager:
    """
    IM 生命周期管理器，负责管理所有 adapter 的启动、运行和停止。
    """
    @Inject()
    def __init__(self, config: GlobalConfig, adapter_registry: AdapterRegistry):
        self.config = config
        self.adapter_registry = adapter_registry
        self.adapters: Dict[str, any] = {}


    def start_adapters(self):
        """
        根据配置文件中的 enable_ims 启动对应的 adapter。
        """
        enable_ims = self.config.ims.enable
        credentials = self.config.ims.configs

        for platform, adapter_keys in enable_ims.items():
            # 动态获取 adapter 类
            adapter_class = self.adapter_registry.get(platform)
            # 动态获取 adapter 的配置类
            config_class = self.adapter_registry.get_config_class(platform)

            for key in adapter_keys:
                # 从 credentials 中读取配置
                if key not in credentials:
                    raise ValueError(f"Credential for key '{key}' is missing in credentials.")
                credential = credentials[key]

                # 动态实例化 adapter 的配置对象
                adapter_config = config_class(**credential)

                # 创建 adapter 实例
                adapter = adapter_class(adapter_config)
                self.adapters[key] = adapter
                adapter.run()

    def stop_adapters(self):
        """
        停止所有已启动的 adapter。
        """
        for key, adapter in self.adapters.items():
            adapter.stop()
            print(f"Stopped adapter: {key}")

    def get_adapters(self) -> Dict[str, any]:
        """
        获取所有已启动的 adapter。
        :return: 已启动的 adapter 字典。
        """
        return self.adapters