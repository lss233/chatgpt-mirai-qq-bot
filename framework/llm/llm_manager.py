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
        for key, backend_config in self.config.llms.backends.items():
            if backend_config.enable:
                self.logger.info(f"Loading backend: {key}")
                self.load_backend(key, backend_config)
    
    def load_backend(self, name: str, backend_config: LLMBackendConfig):
        if name in self.active_backends:
            raise ValueError
        
        adapter_class = self.backend_registry.get(backend_config.adapter)
        config_class = self.backend_registry.get_config_class(backend_config.adapter)
        
        if not adapter_class or not config_class:
            raise ValueError

        configs = [config_class(**config_entry) for config_entry in backend_config.configs]
        
        adapters = []
        
        for config in configs:
            with self.container.scoped() as scoped_container:
                scoped_container.register(config_class, config)
                adapter = Inject(scoped_container).create(adapter_class)()
                adapters.append(adapter)
        self.logger.info(f"Loaded {len(adapters)} adapters for backend: {name}")
        for name in backend_config.models:
            self.active_backends[name] = adapters
        
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