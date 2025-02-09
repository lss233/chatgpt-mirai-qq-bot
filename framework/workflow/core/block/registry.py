from inspect import Parameter, signature
from typing import Dict, List, Tuple, Type, Optional
import warnings
from framework.workflow.core.block import Block
from .schema import BlockConfig, BlockInput, BlockOutput

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
    
    def get_all_types(self) -> List[Type[Block]]:
        """获取所有已注册的 block 类型"""
        return list(self._blocks.values())
    
    def extract_block_info(self, block_type: Type[Block]) -> Tuple[Dict[str, BlockInput], Dict[str, BlockOutput], Dict[str, BlockConfig]]:
        """
        从 Block 类型中提取输入、输出和配置信息，并使用 BlockInput, BlockOutput, BlockConfig 对象封装。

        Args:
            block_type: Block 的类型。

        Returns:
            包含输入、输出和配置信息的字典。
        """
        inputs = {}
        outputs = {}
        configs = {}

        # 获取 Block 类的输入输出定义
        for name, input_info in getattr(block_type, 'inputs', {}).items():
            inputs[name] = BlockInput(
                name=name,
                description=input_info.description,
                type=input_info.data_type.__name__ if hasattr(input_info.data_type, '__name__') else str(input_info.data_type),
                required=True,  # 假设所有输入都是必需的
                default=input_info.default if hasattr(input_info, 'default') else None

            )

        for name, output_info in getattr(block_type, 'outputs', {}).items():
            outputs[name] = BlockOutput(
                name=name,
                description=output_info.description,
                type=output_info.data_type.__name__ if hasattr(output_info.data_type, '__name__') else str(output_info.data_type)
            )
        # 内置方法不属于参数（Block 的 __init__ 方法）
        builtin_params = self.get_builtin_params()

        # 获取 __init__ 方法的参数作为配置
        sig = signature(block_type.__init__)
        for param in sig.parameters.values():
            if param.name == 'self':
                continue
            
            if param.name in builtin_params:
                continue
                
            param_type = param.annotation
            # 解 Optional[T] 类型
            if hasattr(param_type, '__args__') and param_type.__name__ == 'Optional':

                actual_type = param_type.__args__[0]
            else:
                actual_type = param_type

            configs[param.name] = BlockConfig(
                name=param.name,
                description='',  # 暂时没有描述信息
                type=str(actual_type.__name__),
                required=param.default == Parameter.empty,  # 没有默认值则为必需
                default=param.default if param.default != Parameter.empty else None
            )
        return inputs, outputs, configs

    def get_builtin_params(self) -> List[str]:
        """获取内置参数"""
        sig = signature(Block.__init__)
        return [param.name for param in sig.parameters.values()]
