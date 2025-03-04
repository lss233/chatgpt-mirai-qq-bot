from typing import Dict, Optional, Type

from pydantic import BaseModel, Field

from kirara_ai.im.adapter import IMAdapter


class IMAdapterInfo(BaseModel):
    """IM适配器信息"""
    
    name: str
    config_class: Type[BaseModel] = Field(exclude=True)
    adapter_class: Type[IMAdapter] = Field(exclude=True)
    localized_name: Optional[str] = None
    localized_description: Optional[str] = None

class IMRegistry:
    """
    适配器注册表，用于动态注册和管理 adapter。
    """

    _registry: Dict[str, IMAdapterInfo] = {}

    def register(
        self, name: str, adapter_class: Type[IMAdapter], config_class: Type[BaseModel], localized_name: Optional[str] = None, localized_description: Optional[str] = None
    ):
        """
        注册一个新的 adapter 及其配置类。
        :param name: adapter 的名称。
        :param adapter_class: adapter 的类。
        :param config_class: adapter 的配置类。
        """
        self._registry[name] = IMAdapterInfo(
            name=name,
            adapter_class=adapter_class,
            config_class=config_class,
            localized_name=localized_name,
            localized_description=localized_description,
        )

    def unregister(self, name: str):
        """
        注销一个 adapter。
        :param name: adapter 的名称。
        """
        del self._registry[name]

    def get(self, name: str) -> Type[IMAdapter]:
        """
        获取已注册的 adapter 类。
        :param name: adapter 的名称。
        :return: adapter 的类。
        """
        if name not in self._registry:
            raise ValueError(f"IMAdapter with name '{name}' is not registered.")
        return self._registry[name].adapter_class

    def get_config_class(self, name: str) -> Type[BaseModel]:
        """
        获取已注册的 adapter 配置类。
        :param name: adapter 的名称。
        :return: adapter 的配置类。
        """
        if name not in self._registry:
            raise ValueError(f"IMAdapter with name '{name}' is not registered.")
        adapter_info = self._registry[name]
        return adapter_info.config_class

    def get_all_adapters(self) -> Dict[str, IMAdapterInfo]:
        """
        获取所有已注册的 adapter。
        :return: 所有已注册的 adapter。
        """
        return self._registry
