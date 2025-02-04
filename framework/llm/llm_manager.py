from typing import Dict, List, Optional
import random
from framework.config.global_config import GlobalConfig, LLMBackendConfig
from framework.ioc.container import DependencyContainer
from framework.ioc.inject import Inject
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.llm_registry import LLMBackendRegistry
from framework.logger import get_logger

class LLMManager:
    """
    跟踪、管理和调度模型后端
    """
    container: DependencyContainer
    
    config: GlobalConfig
    
    backend_registry: LLMBackendRegistry
    
    active_backends: Dict[str, List[LLMBackendAdapter]]
    
    @Inject()
    def __init__(self, container: DependencyContainer, config: GlobalConfig, backend_registry: LLMBackendRegistry):
        self.container = container
        self.config = config
        self.backend_registry = backend_registry
        self.logger = get_logger("LLMAdapter")
        self.active_backends = {}
    
    def load_config(self):
        """加载配置文件中的所有启用的后端"""
        for backend_id, backend_config in self.config.llms.backends.items():
            if backend_config.enable:
                self.logger.info(f"Loading backend: {backend_id}")
                self.load_backend(backend_id)
    
    def load_backend(self, backend_id: str):
        """
        加载指定的后端
        :param backend_id: 后端ID
        """
        if backend_id not in self.config.llms.backends:
            raise ValueError(f"Backend {backend_id} not found in config")
        
        backend_config = self.config.llms.backends[backend_id]
        if not backend_config.enable:
            raise ValueError(f"Backend {backend_id} is not enabled")
        
        if any(backend_id in adapters for adapters in self.active_backends.values()):
            raise ValueError(f"Backend {backend_id} is already loaded")
        
        adapter_class = self.backend_registry.get(backend_config.adapter)
        config_class = self.backend_registry.get_config_class(backend_config.adapter)
        
        if not adapter_class or not config_class:
            raise ValueError(f"Invalid adapter type: {backend_config.adapter}")

        configs = [config_class(**config_entry) for config_entry in backend_config.configs]
        adapters = []
        
        for config in configs:
            with self.container.scoped() as scoped_container:
                scoped_container.register(config_class, config)
                adapter = Inject(scoped_container).create(adapter_class)()
                adapters.append(adapter)
        
        self.logger.info(f"Loaded {len(adapters)} adapters for backend: {backend_id}")
        for model in backend_config.models:
            if model not in self.active_backends:
                self.active_backends[model] = []
            self.active_backends[model].extend(adapters)
    
    async def unload_backend(self, backend_id: str):
        """
        卸载指定的后端
        :param backend_id: 后端ID
        """
        if backend_id not in self.config.llms.backends:
            raise ValueError(f"Backend {backend_id} not found in config")
        
        backend_config = self.config.llms.backends[backend_id]
        
        # 从所有模型中移除这个后端的适配器
        for model in backend_config.models:
            if model in self.active_backends:
                self.active_backends[model] = []
    
    async def reload_backend(self, backend_id: str):
        """
        重新加载指定的后端
        :param backend_id: 后端ID
        """
        await self.unload_backend(backend_id)
        self.load_backend(backend_id)
    
    def is_backend_available(self, backend_id: str) -> bool:
        """
        检查后端是否可用
        :param backend_id: 后端ID
        :return: 后端是否可用
        """
        if backend_id not in self.config.llms.backends:
            return False
        
        backend_config = self.config.llms.backends[backend_id]
        if not backend_config.enable:
            return False
        
        # 检查后端的所有模型是否都有可用的适配器
        return all(
            model in self.active_backends and len(self.active_backends[model]) > 0
            for model in backend_config.models
        )
    
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