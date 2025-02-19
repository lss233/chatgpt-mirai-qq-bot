from typing import Optional

from pydantic import Field

from framework.im.message import IMMessage
from framework.workflow.core.workflow.registry import WorkflowRegistry

from .base import DispatchRule, RuleConfig


class ChatSenderMatchRuleConfig(RuleConfig):
    """聊天发送者规则配置"""
    sender_id: str = Field(title="发送者ID", description="发送者ID")
    sender_group: str = Field(
        title="发送者群号（可空）", description="发送者群号", default=""
    ) 
    
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

    def get_config(self) -> ChatSenderMatchRuleConfig:
        return ChatSenderMatchRuleConfig(
            sender_id=self.sender_id, sender_group=self.sender_group
        )

    @classmethod
    def from_config(
        cls,
        config: ChatSenderMatchRuleConfig,
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ) -> "ChatSenderMatchRule":
        return cls(config.sender_id, config.sender_group, workflow_registry, workflow_id)

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

    def get_config(self) -> ChatSenderMatchRuleConfig:
        return ChatSenderMatchRuleConfig(
            sender_id=self.sender_id, sender_group=self.sender_group
        )

    @classmethod
    def from_config(
        cls,
        config: ChatSenderMatchRuleConfig,
        workflow_registry: WorkflowRegistry,
        workflow_id: str,
    ) -> "ChatSenderMismatchRule":
        return cls(config.sender_id, config.sender_group, workflow_registry, workflow_id) 