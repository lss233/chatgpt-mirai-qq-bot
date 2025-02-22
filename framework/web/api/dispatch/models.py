from typing import List

from pydantic import BaseModel

from framework.workflow.core.dispatch import CombinedDispatchRule


class DispatchRuleList(BaseModel):
    """调度规则列表"""

    rules: List[CombinedDispatchRule]


class DispatchRuleResponse(BaseModel):
    """调度规则响应"""

    rule: CombinedDispatchRule
