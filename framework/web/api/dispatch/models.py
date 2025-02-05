from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class DispatchRuleConfig(BaseModel):
    """调度规则配置"""
    rule_id: str
    name: str
    description: str
    pattern: str
    priority: int
    workflow_id: str
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None

class DispatchRuleStatus(BaseModel):
    """调度规则状态"""
    rule_id: str
    name: str
    description: str
    pattern: str
    priority: int
    workflow_id: str
    enabled: bool
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool

class DispatchRuleList(BaseModel):
    """调度规则列表响应"""
    rules: List[DispatchRuleStatus]

class DispatchRuleResponse(BaseModel):
    """单个调度规则响应"""
    rule: DispatchRuleStatus 