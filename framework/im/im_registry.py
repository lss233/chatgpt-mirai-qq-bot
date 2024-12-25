from typing import Dict, Type
from pydantic import BaseModel

from framework.im.adapter import IMAdapter

class IMRegistry:
    """
    适配器注册表，用于动态注册和管理 adapter。
    """

    _registry: Dict[str, Type[IMAdapter]] = {}
    _config_registry: Dict[str, Type[BaseModel]] = {}

    def register(self, name: str, adapter_class: Type[IMAdapter], config_class: Type[BaseModel]):
        """
        注册一个新的 adapter 及其配置类。
        :param name: adapter 的名称。
        :param adapter_class: adapter 的类。
        :param config_class: adapter 的配置类。
        """
        if name in self._registry:
            raise ValueError(f"IMAdapter with name '{name}' is already registered.")
        self._registry[name] = adapter_class
        self._config_registry[name] = config_class

    def get(self, name: str) -> Type[IMAdapter]:
        """
        获取已注册的 adapter 类。
        :param name: adapter 的名称。
        :return: adapter 的类。
        """
        if name not in self._registry:
            raise ValueError(f"IMAdapter with name '{name}' is not registered.")
        return self._registry[name]

    def get_config_class(self, name: str) -> Type[BaseModel]:
        """
        获取已注册的 adapter 配置类。
        :param name: adapter 的名称。
        :return: adapter 的配置类。
        """
        if name not in self._config_registry:
            raise ValueError(f"Config class for adapter '{name}' is not registered.")
        return self._config_registry[name]