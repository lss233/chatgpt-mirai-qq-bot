from abc import ABC, abstractmethod

from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse


class LLMBackendAdapter(ABC):
    @abstractmethod
    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        raise NotImplementedError("Unsupported model method")