
from typing import Any, Optional
from pydantic import BaseModel


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
