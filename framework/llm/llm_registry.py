from enum import Enum
from typing import Dict, List, Type
from pydantic import BaseModel

from framework.llm.adapter import LLMBackendAdapter


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
    LLM 注册表，用于动态注册和管理 LLM 适配器及其配置。
    """

    _registry: Dict[str, Type[LLMBackendAdapter]] = {}
    _ability_registry: Dict[str, LLMAbility] = {}
    _config_registry: Dict[str, Type[BaseModel]] = {}

    def register(self, name: str, adapter_class: Type[LLMBackendAdapter], config_class: Type[BaseModel], ability: LLMAbility):
        """
        注册一个新的 LLM 适配器及其支持的能力和配置类。
        :param name: LLM 适配器的名称。
        :param adapter_class: LLM 适配器的类。
        :param ability: LLM 适配器支持的能力。
        :param config_class: LLM 适配器的配置类。
        """
        if name in self._registry:
            raise ValueError(f"LLMAdapter with name '{name}' is already registered.")
        self._registry[name] = adapter_class
        self._ability_registry[name] = ability
        self._config_registry[name] = config_class

    def get_adapter_by_ability(self, ability: LLMAbility) -> List[Type[LLMBackendAdapter]]:
        """
        根据指定的能力获取严格符合要求的 LLM 适配器列表。
        :param ability: 指定的能力。
        :return: 符合要求的 LLM 适配器列表。
        """
        return [adapter_class for name, adapter_class in self._registry.items() if self._ability_registry[name] == ability.value]
    def search_adapter_by_ability(self, ability: LLMAbility) -> List[Type[LLMBackendAdapter]]:
        """
        根据指定的能力模糊搜索具备该能力的 LLM 适配器列表。
        :param ability: 指定的能力。
        :return: 具备该能力的 LLM 适配器列表。
        """
        return [adapter_class for name, adapter_class in self._registry.items() if self._ability_registry[name].value & ability.value == ability.value]

    def get(self, name: str) -> Type[LLMBackendAdapter]:
        """
        获取已注册的 LLM 适配器类。
        :param name: LLM 适配器的名称。
        :return: LLM 适配器的类。
        """
        if name not in self._registry:
            raise ValueError(f"LLMAdapter with name '{name}' is not registered.")
        return self._registry[name]

    def get_config_class(self, name: str) -> Type[BaseModel]:
        """
        获取已注册的 LLM 适配器的配置类。
        :param name: LLM 适配器的名称。
        :return: LLM 适配器的配置类。
        """
        if name not in self._config_registry:
            raise ValueError(f"Config class for LLMAdapter '{name}' is not registered.")
        return self._config_registry[name]
    
    def get_ability(self, name: str) -> LLMAbility:
        """
        获取已注册的 LLM 适配器能力。
        :param name: LLM 适配器的名称。
        :return: LLM 适配器的能力。
        """
        if name not in self._ability_registry:
            raise ValueError(f"LLMAdapter with name '{name}' is not registered.")
        return self._ability_registry[name]