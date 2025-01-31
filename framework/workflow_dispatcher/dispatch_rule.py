from abc import ABC, abstractmethod
from typing import Type
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow_executor.workflow import Workflow

class DispatchRule(ABC):
    """
    工作流调度规则的抽象基类。
    用于定义如何根据消息内容选择合适的工作流进行处理。
    """
    
    def __init__(self, workflow_factory):
        """
        初始化调度规则。
        
        Args:
            workflow_factory: 用于构造工作流的工厂对象
        """
        self.workflow_factory = workflow_factory
    
    @abstractmethod
    def match(self, message: IMMessage) -> bool:
        """
        判断消息是否匹配该规则。
        
        Args:
            message: 待匹配的消息
            
        Returns:
            bool: 是否匹配
        """
        pass
    
    def get_workflow(self, container: DependencyContainer) -> Workflow:
        """
        通过工厂获取该规则对应的工作流实例。
        
        Returns:
            Workflow: 工作流实例
        """
        return self.workflow_factory.create_workflow(container)
    
    def __str__(self) -> str:
        return self.__class__.__name__


class PrefixMatchRule(DispatchRule):
    """根据消息前缀匹配的规则"""
    
    def __init__(self, prefix: str, workflow_factory):
        super().__init__(workflow_factory)
        self.prefix = prefix
        
    def match(self, message: IMMessage) -> bool:
        return message.content.startswith(self.prefix)
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(prefix='{self.prefix}')"


class KeywordMatchRule(DispatchRule):
    """根据关键词匹配的规则"""
    
    def __init__(self, keywords: list[str], workflow_factory):
        super().__init__(workflow_factory)
        self.keywords = keywords
        
    def match(self, message: IMMessage) -> bool:
        return any(keyword in message.content for keyword in self.keywords)
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(keywords={self.keywords})"


class RegexMatchRule(DispatchRule):
    """根据正则表达式匹配的规则"""
    
    def __init__(self, pattern: str, workflow_factory):
        super().__init__(workflow_factory)
        import re
        self.pattern = re.compile(pattern)
        
    def match(self, message: IMMessage) -> bool:
        return bool(self.pattern.search(message.content))
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(pattern='{self.pattern.pattern}')"


class FallbackMatchRule(DispatchRule):
    """默认的兜底规则，总是匹配"""
    
    def __init__(self, workflow_factory):
        super().__init__(workflow_factory)
        
    def match(self, message: IMMessage) -> bool:
        return True
