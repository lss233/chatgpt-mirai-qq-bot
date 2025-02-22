from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from kirara_ai.llm.format.request import LLMChatRequest
from kirara_ai.llm.format.response import LLMChatResponse


@runtime_checkable
class AutoDetectModelsProtocol(Protocol):
    async def auto_detect_models(self) -> list[str]: ...


class LLMBackendAdapter(ABC):
    @abstractmethod
    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        raise NotImplementedError("Unsupported model method")
