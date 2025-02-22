from typing import Callable, List, Optional, TypeVar

from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block

T = TypeVar("T")
OptionsProvider = Callable[[DependencyContainer, Block], List[T]]

class ParamMeta:
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, options_provider: Optional[OptionsProvider[T]] = None):
        self.label = label
        self.description = description
        self.options_provider = options_provider

    def __repr__(self):
        return f"ParamMeta(label={self.label}, description={self.description}, options_provider={self.options_provider})"

    def __str__(self):
        return self.__repr__()
    
    def get_options(self, block: Block) -> List[T]:
        if self.options_provider:
            return self.options_provider(block)
        return []
    
