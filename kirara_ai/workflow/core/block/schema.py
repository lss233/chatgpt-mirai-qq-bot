from typing import Any, List, Optional

from pydantic import BaseModel, Field

from kirara_ai.workflow.core.block.param import OptionsProvider


class BlockInput(BaseModel):
    """Block输入定义"""

    name: str
    label: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None


class BlockOutput(BaseModel):
    """Block输出定义"""

    name: str
    label: str
    description: str
    type: str


class BlockConfig(BaseModel):
    """Block配置项定义"""

    name: str
    description: Optional[str] = None
    type: str
    required: bool = True
    default: Optional[Any] = None
    label: Optional[str] = None
    has_options: bool = False
    options: Optional[List[Any]] = None
    options_provider: Optional[OptionsProvider] = Field(exclude=True)
