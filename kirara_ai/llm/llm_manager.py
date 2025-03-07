import random
from typing import Dict, List, Optional

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.ioc.inject import Inject
from kirara_ai.llm.adapter import LLMBackendAdapter
from kirara_ai.llm.llm_registry import LLMAbility, LLMBackendRegistry
from kirara_ai.logger import get_logger


class LLMManager:
    """
    跟踪、管理和调度模型后端
    """

    container: DependencyContainer
    config: GlobalConfig
    backend_registry: LLMBackendRegistry
    active_backends: Dict[str, List[LLMBackendAdapter]]

    @Inject()
    def __init__(
        self,
        container: DependencyContainer,
        config: GlobalConfig,
        backend_registry: LLMBackendRegistry,
    ):
        self.container = container
        self.config = config
        self.backend_registry = backend_registry
        self.logger = get_logger("LLMAdapter")
        self.active_backends = {}
        self.backends: Dict[str, LLMBackendAdapter] = {}

    def load_config(self):
        """加载配置文件中的所有启用的后端"""
        for backend in self.config.llms.api_backends:
            if backend.enable:
                self.logger.info(f"Loading backend: {backend.name}")
                try:
                    self.load_backend(backend.name)
                except Exception as e:
                    self.logger.error(f"Failed to load backend {backend.name}: {e}")

    def load_backend(self, backend_name: str):
        """
        加载指定的后端
        :param backend_name: 后端名称
        """
        backend = next(
            (b for b in self.config.llms.api_backends if b.name == backend_name), None
        )
        if not backend:
            raise ValueError(f"Backend {backend_name} not found in config")

        if not backend.enable:
            raise ValueError(f"Backend {backend_name} is not enabled")

        if any(backend_name in adapters for adapters in self.active_backends.values()):
            raise ValueError(f"Backend {backend_name} is already loaded")

        adapter_class = self.backend_registry.get(backend.adapter)
        config_class = self.backend_registry.get_config_class(backend.adapter)

        if not adapter_class or not config_class:
            raise ValueError(f"Invalid adapter type: {backend.adapter}")

        # 创建适配器实例
        with self.container.scoped() as scoped_container:
            scoped_container.register(config_class, config_class(**backend.config))
            adapter = Inject(scoped_container).create(adapter_class)()
            self.backends[backend_name] = adapter

            # 注册到每个支持的模型
            for model in backend.models:
                if model not in self.active_backends:
                    self.active_backends[model] = []
                self.active_backends[model].append(adapter)

        self.logger.info(f"Backend {backend_name} loaded successfully")

    async def unload_backend(self, backend_name: str):
        """
        卸载指定的后端
        :param backend_name: 后端名称
        """
        backend = next(
            (b for b in self.config.llms.api_backends if b.name == backend_name), None
        )
        backend = self.backends.get(backend_name)
        if not backend:
            raise ValueError(f"Backend {backend_name} not found in config")

        # 从所有模型中移除这个后端的适配器
        all_models = list(self.active_backends.keys())
        for model in all_models:
            if backend in self.active_backends[model]:
                self.active_backends[model].remove(backend)
            if len(self.active_backends[model]) == 0:
                self.active_backends.pop(model)
        self.backends.pop(backend_name)

    async def reload_backend(self, backend_name: str):
        """
        重新加载指定的后端
        :param backend_name: 后端名称
        """
        await self.unload_backend(backend_name)
        self.load_backend(backend_name)

    def is_backend_available(self, backend_name: str) -> bool:
        """
        检查后端是否可用
        :param backend_name: 后端名称
        :return: 后端是否可用
        """
        backend = next(
            (b for b in self.config.llms.api_backends if b.name == backend_name), None
        )
        if not backend:
            return False

        if not backend.enable:
            return False

        # 检查后端的所有模型是否都有可用的适配器
        return all(
            model in self.active_backends and len(self.active_backends[model]) > 0
            for model in backend.models
        )

    def get(self, backend_name: str) -> Optional[LLMBackendAdapter]:
        """
        获取指定后端的适配器实例
        :param backend_name: 后端名称
        :return: LLM适配器实例,如果没有找到则返回None
        """
        return self.backends.get(backend_name)

    def get_llm(self, model_id: str) -> Optional[LLMBackendAdapter]:
        """
        从指定模型的活跃后端中随机返回一个适配器实例
        :param model_id: 模型ID
        :return: LLM适配器实例,如果没有找到则返回None
        """
        if model_id not in self.active_backends:
            return None

        backends = self.active_backends[model_id]
        if not backends:
            return None
        # TODO: 后续考虑支持更多的选择策略
        return random.choice(backends)
    
    def get_supported_models(self, ability: LLMAbility) -> List[str]:
        """
        获取所有支持的模型
        :return: 支持的模型列表
        """
        adapter_types = self.backend_registry.search_adapter_by_ability(ability)
        matched_backends = set()
        for backend_id, backends in self.active_backends.items():
            for backend in backends:
                for adapter_type in adapter_types:
                    if isinstance(backend, adapter_type):
                        matched_backends.add(backend_id)
                        break

        if not matched_backends:
            return []
        return list(matched_backends)

    def get_llm_id_by_ability(self, ability: LLMAbility) -> str:
        """
        根据指定的能力获取严格符合要求的 LLM 适配器列表。
        :param ability: 指定的能力。
        :return: 符合要求的 LLM 适配器列表。
        """
        supported_models = self.get_supported_models(ability)
        if not supported_models:
            return None
        return random.choice(supported_models)
