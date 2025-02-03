from typing import Dict, Type, Optional
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
        
    def get(self, full_name: str) -> Optional[Type[Block]]:
        """获取已注册的 block 类"""
        return self._blocks.get(full_name)
    
    def clear(self):
        """清空注册表（主要用于测试）"""
        self._blocks.clear() 