from kirara_ai.llm.adapter import LLMBackendAdapter


class LLMAdapterEvent:
    def __init__(self, adapter: LLMBackendAdapter):
        self.adapter = adapter
        
    def __repr__(self):
        return f"{self.__class__.__name__}(adapter={self.adapter})"

class LLMAdapterLoaded(LLMAdapterEvent):
    pass

class LLMAdapterUnloaded(LLMAdapterEvent):
    pass


