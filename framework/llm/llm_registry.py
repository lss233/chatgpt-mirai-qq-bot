from enum import Enum
from typing import Dict, List, Type, Optional
from pydantic import BaseModel

from framework.llm.adapter import LLMBackendAdapter
from framework.config.global_config import LLMBackendConfig

class LLMAbility(Enum):
    """
    定义了 LLMAbility 的枚举类型，用于表示 LLM 的能力。
    """
    # 这里表示接口支持 chat 格式的对话
    Chat = 1 << 1
    TextInput = 1 << 2
    TextOutput = 1 << 3
    ImageInput = 1 << 4
    ImageOutput = 1 << 5
    AudioInput = 1 << 6
    AudioOutput = 1 << 7
    # 下面是通过位运算组合能力
    TextCompletion = TextInput | TextOutput
    TextChat = Chat | TextCompletion
    ImageGeneration = ImageInput | ImageOutput
    TextImageMultiModal = Chat | ImageGeneration
    TextImageAudioMultiModal = TextImageMultiModal | AudioInput | AudioOutput
    
class LLMBackendRegistry:
    """
    LLM后端注册表
    """
    _adapters: Dict[str, Type[LLMBackendAdapter]]
    _configs: Dict[str, Type[LLMBackendConfig]]
    _ability_registry: Dict[str, int]
    
    def __init__(self):
        self._adapters = {}
        self._configs = {}
    
    def register(self, adapter_type: str, adapter_class: Type[LLMBackendAdapter], config_class: Type[LLMBackendConfig]):
        """
        注册一个LLM后端适配器
        :param adapter_type: 适配器类型
        :param adapter_class: 适配器类
        :param config_class: 配置类
        """
        self._adapters[adapter_type] = adapter_class
        self._configs[adapter_type] = config_class
    
    def get(self, adapter_type: str) -> Optional[Type[LLMBackendAdapter]]:
        """
        获取指定类型的适配器类
        :param adapter_type: 适配器类型
        :return: 适配器类,如果没有找到则返回None
        """
        return self._adapters.get(adapter_type)
    
    def get_config_class(self, adapter_type: str) -> Optional[Type[LLMBackendConfig]]:
        """
        获取指定类型的配置类
        :param adapter_type: 适配器类型
        :return: 配置类,如果没有找到则返回None
        """
        return self._configs.get(adapter_type)
    
    def get_adapter_types(self) -> list[str]:
        """
        获取所有已注册的适配器类型
        :return: 适配器类型列表
        """
        return list(self._adapters.keys())

    def get_adapter_by_ability(self, ability: LLMAbility) -> List[Type[LLMBackendAdapter]]:
        """
        根据指定的能力获取严格符合要求的 LLM 适配器列表。
        :param ability: 指定的能力。
        :return: 符合要求的 LLM 适配器列表。
        """
        return [adapter_class for name, adapter_class in self._adapters.items() if self._ability_registry[name] == ability.value]
    def search_adapter_by_ability(self, ability: LLMAbility) -> List[Type[LLMBackendAdapter]]:
        """
        根据指定的能力模糊搜索具备该能力的 LLM 适配器列表。
        :param ability: 指定的能力。
        :return: 具备该能力的 LLM 适配器列表。
        """
        return [adapter_class for name, adapter_class in self._adapters.items() if self._ability_registry[name].value & ability.value == ability.value]

    def get_all_adapters(self) -> Dict[str, Type[LLMBackendAdapter]]:
        """
        获取所有已注册的 LLM 适配器。
        :return: 所有已注册的 LLM 适配器字典。
        """
        return self._adapters.copy()