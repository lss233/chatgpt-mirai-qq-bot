from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class BlockInput(BaseModel):
    """Block输入定义"""
    name: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None

class BlockOutput(BaseModel):
    """Block输出定义"""
    name: str
    description: str
    type: str

class BlockConfig(BaseModel):
    """Block配置项定义"""
    name: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None

class BlockType(BaseModel):
    """Block类型信息"""
    type_name: str
    name: str
    description: str
    inputs: List[BlockInput]
    outputs: List[BlockOutput]
    configs: List[BlockConfig]

class BlockTypeList(BaseModel):
    """Block类型列表响应"""
    types: List[BlockType]

class BlockTypeResponse(BaseModel):
    """单个Block类型响应"""
    type: BlockType 