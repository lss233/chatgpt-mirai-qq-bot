from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class DispatchRuleConfig(BaseModel):
    """调度规则配置"""
    rule_id: str
    name: str
    description: str = ""
    type: str
    priority: int = 5
    workflow_id: str
    enabled: bool = True
    config: Dict[str, Any] = {}  # 用于存储规则类型特定的配置
    metadata: Dict[str, Any] = {}  # 用于存储其他元数据

class DispatchRuleStatus(BaseModel):
    """调度规则状态"""
    rule_id: str
    name: str
    description: str
    type: str  # 规则类型
    priority: int
    workflow_id: str
    enabled: bool
    config: Dict[str, Any]  # 规则类型特定的配置
    metadata: Dict[str, Any]
    is_active: bool

class DispatchRuleList(BaseModel):
    """调度规则列表"""
    rules: List[DispatchRuleStatus]

class DispatchRuleResponse(BaseModel):
    """调度规则响应"""
    rule: DispatchRuleStatus 