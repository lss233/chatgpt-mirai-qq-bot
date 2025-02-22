from typing import List

from pydantic import BaseModel

from kirara_ai.workflow.core.block.schema import BlockConfig, BlockInput, BlockOutput


class BlockType(BaseModel):
    """Block类型信息"""

    type_name: str
    name: str
    label: str
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
