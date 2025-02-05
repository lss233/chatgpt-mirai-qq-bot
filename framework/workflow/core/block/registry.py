from typing import Dict, Type, Optional
import warnings
from framework.workflow.core.block import Block

class BlockRegistry:
    """Block 注册表，用于管理所有已注册的 block"""
    
    def __init__(self):
        self._blocks = {}
    
    def register(self, block_id: str, group_id: str, block_class: Type[Block]):
        """注册一个 block
        
        Args:
            block_id: block 的唯一标识
            group_id: 组标识（internal 为框架内置）
            block_class: block 类
        """
        full_name = f"{group_id}:{block_id}"
        if full_name in self._blocks:
            raise ValueError(f"Block {full_name} already registered")
        self._blocks[full_name] = block_class
        block_class.id = block_id
        
    def get(self, full_name: str) -> Optional[Type[Block]]:
        """获取已注册的 block 类"""
        return self._blocks.get(full_name)
    
    def clear(self):
        """清空注册表"""
        self._blocks.clear() 

    def get_block_type_name(self, block_class: Type[Block]) -> str:
        """获取 block 的类型名称，优先使用注册名称"""
        # 遍历注册表查找匹配的 block 类
        for full_name, registered_class in self._blocks.items():
            if registered_class == block_class:
                return full_name
                
        warnings.warn(
            f"Block class {block_class.__name__} is not registered. Using class path instead.",
            UserWarning
        )
        return f"!!{block_class.__module__}.{block_class.__name__}"