from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse


@runtime_checkable
class AutoDetectModelsProtocol(Protocol):
    async def auto_detect_models(self) -> list[str]: ...


class LLMBackendAdapter(ABC):
    @abstractmethod
    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        raise NotImplementedError("Unsupported model method")
