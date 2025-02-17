import random
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, Field

from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.workflow import Workflow
from framework.workflow.core.workflow.registry import WorkflowRegistry


class RuleConfig(BaseModel):
    """规则配置的基类"""



class RegexRuleConfig(RuleConfig):
    """正则规则配置"""

    pattern: str = Field(title="正则表达式", description="正则表达式")


class PrefixRuleConfig(RuleConfig):
    """前缀规则配置"""

    prefix: str = Field(title="前缀", description="前缀")


class KeywordRuleConfig(RuleConfig):
    """关键词规则配置"""

    keywords: List[str] = Field(title="关键词", description="关键词列表")


class RandomChanceRuleConfig(RuleConfig):
    """随机概率规则配置"""

    chance: int = Field(
        default=50, ge=0, le=100, title="随机概率", description="随机概率，范围为0-100"
    )


class ChatSenderMatchRuleConfig(RuleConfig):
    """聊天发送者规则配置"""

    sender_id: str = Field(title="发送者ID", description="发送者ID")
    sender_group: str = Field(
        title="发送者群号（可空）", description="发送者群号", default=""
    )


class SimpleDispatchRule(BaseModel):
    """简单规则，包含规则类型和配置"""

    type: str
    config: Dict[str, Any]


class RuleGroup(BaseModel):
    """规则组，包含多个简单规则和组合操作符"""

    operator: Literal["and", "or"] = "or"
    rules: List[SimpleDispatchRule]


class CombinedDispatchRule(BaseModel):
    """组合调度规则，支持复杂的规则组合"""

    rule_id: str
    name: str
    description: str = ""
    workflow_id: str
    priority: int = 5
    enabled: bool = True
    rule_groups: List[RuleGroup]  # 规则组之间是 AND 关系
    metadata: Dict[str, Any] = {}

    def match(self, message: IMMessage, workflow_registry: WorkflowRegistry) -> bool:
        """
        判断消息是否匹配该规则。
        规则组之间是 AND 关系，规则组内部根据 operator 决定是 AND 还是 OR 关系。

        Args:
            message: 待匹配的消息
            workflow_registry: 工作流注册表，用于创建具体的规则实例

        Returns:
            bool: 是否匹配
        """
        # 如果规则被禁用，直接返回 False
        if not self.enabled:
            return False

        # 所有规则组都必须匹配（AND 关系）
        for group in self.rule_groups:
            # 获取组内所有规则的匹配结果
            rule_results = []
            for rule in group.rules:
                try:
                    # 创建具体的规则实例
                    rule_class = DispatchRule.get_rule_type(rule.type)
                    rule_instance = rule_class.from_config(
                        rule_class.config_class(**rule.config),
                        workflow_registry,
                        self.workflow_id,
                    )
                    rule_results.append(rule_instance.match(message))
                except Exception as e:
                    # 如果规则创建或匹配过程出错，视为不匹配
                    continue

            # 根据操作符确定组的匹配结果
            if not rule_results:  # 如果组内没有有效规则，视为不匹配
                return False

            if group.operator == "and":
                if not all(rule_results):  # AND 关系：所有规则都必须匹配
                    return False
            else:  # operator == "or"
                if not any(rule_results):  # OR 关系：至少一个规则匹配
                    return False

        # 所有规则组都匹配成功
        return True

    def get_workflow(self, container: DependencyContainer) -> Workflow:
        """
        获取该规则对应的工作流实例。

        Args:
            container: 依赖注入容器
            workflow_registry: 工作流注册表

        Returns:
            Workflow: 工作流实例
        """
        return container.resolve(WorkflowRegistry).get(self.workflow_id, container)


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

    @classmethod
    @abstractmethod
    def from_config(
        cls, config: RuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str
    ) -> "DispatchRule":
        """从配置创建规则实例"""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', priority={self.priority}, enabled={self.enabled})"


class RegexMatchRule(DispatchRule):
    """根据正则表达式匹配的规则"""

    config_class = RegexRuleConfig
    type_name = "regex"

    def __init__(
        self, pattern: str, workflow_registry: WorkflowRegistry, workflow_id: str
    ):
        super().__init__(workflow_registry, workflow_id)
        import re

        self.pattern = re.compile(pattern)

    def match(self, message: IMMessage) -> bool:
        return bool(self.pattern.search(message.content))

    def get_config(self) -> RegexRuleConfig:
        return RegexRuleConfig(pattern=self.pattern.pattern)

    @classmethod
    def from_config(
        cls,
        config: RegexRuleConfig,
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ) -> "RegexMatchRule":
        return cls(config.pattern, workflow_registry, workflow_id)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', pattern='{self.pattern.pattern}', priority={self.priority}, enabled={self.enabled})"


class PrefixMatchRule(DispatchRule):
    """根据消息前缀匹配的规则"""

    config_class = PrefixRuleConfig
    type_name = "prefix"

    def __init__(
        self, prefix: str, workflow_registry: WorkflowRegistry, workflow_id: str
    ):
        super().__init__(workflow_registry, workflow_id)
        self.prefix = prefix

    def match(self, message: IMMessage) -> bool:
        return message.content.startswith(self.prefix)

    def get_config(self) -> PrefixRuleConfig:
        return PrefixRuleConfig(prefix=self.prefix)

    @classmethod
    def from_config(
        cls,
        config: PrefixRuleConfig,
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ) -> "PrefixMatchRule":
        return cls(config.prefix, workflow_registry, workflow_id)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', prefix='{self.prefix}', priority={self.priority}, enabled={self.enabled})"


class KeywordMatchRule(DispatchRule):
    """根据关键词匹配的规则"""

    config_class = KeywordRuleConfig
    type_name = "keyword"

    def __init__(
        self, keywords: List[str], workflow_registry: WorkflowRegistry, workflow_id: str
    ):
        super().__init__(workflow_registry, workflow_id)
        self.keywords = keywords

    def match(self, message: IMMessage) -> bool:
        return any(keyword in message.content for keyword in self.keywords)

    def get_config(self) -> KeywordRuleConfig:
        return KeywordRuleConfig(keywords=self.keywords)

    @classmethod
    def from_config(
        cls,
        config: KeywordRuleConfig,
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ) -> "KeywordMatchRule":
        return cls(config.keywords, workflow_registry, workflow_id)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.rule_id}', keywords={self.keywords}, priority={self.priority}, enabled={self.enabled})"


class RandomChanceMatchRule(DispatchRule):
    """根据随机概率匹配的规则"""

    config_class = RandomChanceRuleConfig
    type_name = "random"

    def __init__(
        self, chance: float, workflow_registry: WorkflowRegistry, workflow_id: str
    ):
        super().__init__(workflow_registry, workflow_id)
        self.chance = chance

    def match(self, message: IMMessage) -> bool:
        return random.random() / 100 < self.chance


class ChatSenderMatchRule(DispatchRule):
    """根据聊天发送者匹配的规则"""

    config_class = ChatSenderMatchRuleConfig
    type_name = "sender"

    def __init__(
        self,
        sender_id: str,
        sender_group: Optional[str],
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ):
        super().__init__(workflow_registry, workflow_id)
        self.sender_id = sender_id
        self.sender_group = sender_group

    def match(self, message: IMMessage) -> bool:
        if self.sender_group:
            match_group = message.sender.group_id == self.sender_group
        else:
            match_group = True
        return match_group and message.sender.user_id == self.sender_id


class ChatSenderMismatchRule(DispatchRule):
    """根据聊天发送者不匹配的规则"""

    config_class = ChatSenderMatchRuleConfig
    type_name = "sender_mismatch"

    def __init__(
        self,
        sender_id: str,
        sender_group: Optional[str],
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ):
        super().__init__(workflow_registry, workflow_id)
        self.sender_id = sender_id
        self.sender_group = sender_group

    def match(self, message: IMMessage) -> bool:
        if self.sender_group:
            match_group = message.sender.group_id != self.sender_group
        else:
            match_group = True
        return match_group and message.sender.user_id != self.sender_id


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
    def from_config(
        cls, config: RuleConfig, workflow_registry: WorkflowRegistry, workflow_id: str
    ) -> "FallbackMatchRule":
        return cls(workflow_registry, workflow_id)


# 注册所有规则类型
DispatchRule.register_rule_type(RegexMatchRule)
DispatchRule.register_rule_type(PrefixMatchRule)
DispatchRule.register_rule_type(KeywordMatchRule)
DispatchRule.register_rule_type(FallbackMatchRule)
DispatchRule.register_rule_type(RandomChanceMatchRule)
DispatchRule.register_rule_type(ChatSenderMatchRule)
DispatchRule.register_rule_type(ChatSenderMismatchRule)
