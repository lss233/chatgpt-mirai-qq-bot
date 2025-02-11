from abc import ABC, abstractmethod
from typing import Type, Callable, Dict, Any, Optional, List, ClassVar
from pydantic import BaseModel
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.workflow import Workflow
from framework.workflow.core.workflow.registry import WorkflowRegistry

class RuleConfig(BaseModel):
    """规则配置的基类"""
    pass

class RegexRuleConfig(RuleConfig):
    """正则规则配置"""
    pattern: str

class PrefixRuleConfig(RuleConfig):
    """前缀规则配置"""
    prefix: str

class KeywordRuleConfig(RuleConfig):
    """关键词规则配置"""
    keywords: List[str]

class DispatchRule(ABC):
    """
    工作流调度规则的抽象基类。
    用于定义如何根据消息内容选择合适的工作流进行处理。
    """
    # 类变量，用于规则类型注册
    rule_types: ClassVar[Dict[str, Type["DispatchRule"]]] = {}
    config_class: ClassVar[Type[RuleConfig]]
    type_name: ClassVar[str]
    
    def __init__(self, workflow_registry: WorkflowRegistry, workflow_id: str):
        """
        初始化调度规则。
        
        Args:
            workflow_id: 工作流ID
        """
        self.workflow_registry = workflow_registry
        self.rule_id: str = ""
        self.name: str = ""
        self.description: str = ""
        self.priority: int = 5  # 默认优先级为5
        self.enabled: bool = True  # 是否启用
        self.metadata: Dict[str, Any] = {}  # 元数据
        self.workflow_id: str = workflow_id
    
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
        return self.workflow_registry.get(self.workflow_id, container)
    
    @classmethod
    def register_rule_type(cls, rule_class: Type["DispatchRule"]):
        """注册规则类型"""
        cls.rule_types[rule_class.type_name] = rule_class
        
    @classmethod
    def get_rule_type(cls, type_name: str) -> Type["DispatchRule"]:
        """获取规则类型"""
        if type_name not in cls.rule_types:
            raise ValueError(f"Unknown rule type: {type_name}")
        return cls.rule_types[type_name]
        
    @abstractmethod
    def get_config(self) -> RuleConfig:
        """获取规则配置"""
        pass
        
    @classmethod
    @abstractmethod
    def from_config(cls, config: RuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str) -> "DispatchRule":
        """从配置创建规则实例"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', priority={self.priority}, enabled={self.enabled})"


class RegexMatchRule(DispatchRule):
    """根据正则表达式匹配的规则"""
    config_class = RegexRuleConfig
    type_name = "regex"
    
    def __init__(self, pattern: str, workflow_registry: WorkflowRegistry, workflow_id: str):
        super().__init__(workflow_registry, workflow_id)
        import re
        self.pattern = re.compile(pattern)
        
    def match(self, message: IMMessage) -> bool:
        return bool(self.pattern.search(message.content))
        
    def get_config(self) -> RegexRuleConfig:
        return RegexRuleConfig(pattern=self.pattern.pattern)
        
    @classmethod
    def from_config(cls, config: RegexRuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str) -> "RegexMatchRule":
        return cls(config.pattern, workflow_registry, workflow_id)
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', pattern='{self.pattern.pattern}', priority={self.priority}, enabled={self.enabled})"


class PrefixMatchRule(DispatchRule):
    """根据消息前缀匹配的规则"""
    config_class = PrefixRuleConfig
    type_name = "prefix"
    
    def __init__(self, prefix: str, workflow_registry: WorkflowRegistry, workflow_id: str):
        super().__init__(workflow_registry, workflow_id)
        self.prefix = prefix
        
    def match(self, message: IMMessage) -> bool:
        return message.content.startswith(self.prefix)
        
    def get_config(self) -> PrefixRuleConfig:
        return PrefixRuleConfig(prefix=self.prefix)
        
    @classmethod
    def from_config(cls, config: PrefixRuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str) -> "PrefixMatchRule":
        return cls(config.prefix, workflow_registry, workflow_id)
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', prefix='{self.prefix}', priority={self.priority}, enabled={self.enabled})"


class KeywordMatchRule(DispatchRule):
    """根据关键词匹配的规则"""
    config_class = KeywordRuleConfig
    type_name = "keyword"
    
    def __init__(self, keywords: List[str], workflow_registry: WorkflowRegistry, workflow_id: str):
        super().__init__(workflow_registry, workflow_id)
        self.keywords = keywords
        
    def match(self, message: IMMessage) -> bool:
        return any(keyword in message.content for keyword in self.keywords)
        
    def get_config(self) -> KeywordRuleConfig:
        return KeywordRuleConfig(keywords=self.keywords)
        
    @classmethod
    def from_config(cls, config: KeywordRuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str) -> "KeywordMatchRule":
        return cls(config.keywords, workflow_registry, workflow_id)
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', keywords={self.keywords}, priority={self.priority}, enabled={self.enabled})"


class FallbackMatchRule(DispatchRule):
    """默认的兜底规则，总是匹配"""
    config_class = RuleConfig
    type_name = "fallback"
    
    def __init__(self, workflow_registry: WorkflowRegistry, workflow_id: str):
        super().__init__(workflow_registry, workflow_id)
        self.priority = 0  # 兜底规则优先级最低
        
    def match(self, message: IMMessage) -> bool:
        return True
        
    def get_config(self) -> RuleConfig:
        return RuleConfig()
        
    @classmethod
    def from_config(cls, config: RuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str) -> "FallbackMatchRule":
        return cls(workflow_registry, workflow_id)


# 注册所有规则类型
DispatchRule.register_rule_type(RegexMatchRule)
DispatchRule.register_rule_type(PrefixMatchRule)
DispatchRule.register_rule_type(KeywordMatchRule)
DispatchRule.register_rule_type(FallbackMatchRule)
