import warnings
from inspect import Parameter, signature
from typing import Annotated, Dict, List, Optional, Tuple, Type, Union, get_args, get_origin

from framework.workflow.core.block import Block
from framework.workflow.core.block.param import ParamMeta

from .schema import BlockConfig, BlockInput, BlockOutput


def extract_block_param(param):
    """
    提取 Block 参数信息，包括类型字符串、标签、是否必需、描述和默认值。
    """
    param_type = param.annotation
    required = True
    label = param.name
    description = None
    default = param.default if param.default != Parameter.empty else None

    if get_origin(param_type) is Annotated:
        args = get_args(param_type)
        if len(args) > 0:
            actual_type = args[0]
            metadata = args[1] if len(args) > 1 else None

            if isinstance(metadata, ParamMeta):
                label = metadata.label
                description = metadata.description

            # 递归调用 extract_block_param 处理实际类型
            block_config = extract_block_param(
                Parameter(
                    name=param.name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=actual_type,
                    default=default,
                )
            )
            type_string = block_config.type
            required = block_config.required  # 继承 required 属性
        else:
            type_string = "Any"
    elif get_origin(param_type) is Union:
        args = get_args(param_type)
        # 检查 Union 中是否包含 NoneType
        if type(None) in args:
            required = False
            # 移除 NoneType，并递归处理剩余的类型
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                block_config = extract_block_param(
                    Parameter(
                        name=param.name,
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=non_none_args[0],
                        default=default,
                    )
                )
                type_string = block_config.type
            else:
                # 如果 Union 中包含多个非 NoneType，则返回 Union 类型
                type_string = (
                    f"Union[{', '.join(get_type_name(arg) for arg in non_none_args)}]"
                )
        else:
            # 如果 Union 中不包含 NoneType，则直接返回 Union 类型
            type_string = f"Union[{', '.join(get_type_name(arg) for arg in args)}]"
    else:
        type_string = get_type_name(param_type)

    return BlockConfig(
        name=param.name,  # 设置名称
        description=description,
        type=type_string,
        required=required,
        default=default,  # 设置默认值
        label=label,
    )


def get_type_name(type_obj):
    """
    获取类型的名称。
    """
    if hasattr(type_obj, "__name__"):
        return type_obj.__name__
    return str(type_obj)


class BlockRegistry:
    """Block 注册表，用于管理所有已注册的 block"""

    def __init__(self):
        self._blocks = {}
        self._localized_names = {}

    def register(
        self,
        block_id: str,
        group_id: str,
        block_class: Type[Block],
        localized_name: Optional[str] = None,
    ):
        """注册一个 block

        Args:
            block_id: block 的唯一标识
            group_id: 组标识（internal 为框架内置）
            block_class: block 类
            localized_name: 本地化名称
        """
        full_name = f"{group_id}:{block_id}"
        if full_name in self._blocks:
            raise ValueError(f"Block {full_name} already registered")
        self._blocks[full_name] = block_class
        block_class.id = block_id
        if localized_name:
            self._localized_names[full_name] = localized_name

    def get(self, full_name: str) -> Optional[Type[Block]]:
        """获取已注册的 block 类"""
        return self._blocks.get(full_name)

    def get_localized_name(self, block_id: str) -> Optional[str]:
        """获取本地化名称"""
        return self._localized_names.get(block_id, block_id)

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
            UserWarning,
        )
        return f"!!{block_class.__module__}.{block_class.__name__}"

    def get_all_types(self) -> List[Type[Block]]:
        """获取所有已注册的 block 类型"""
        return list(self._blocks.values())

    def extract_block_info(
        self, block_type: Type[Block]
    ) -> Tuple[Dict[str, BlockInput], Dict[str, BlockOutput], Dict[str, BlockConfig]]:
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
        for name, input_info in getattr(block_type, "inputs", {}).items():
            inputs[name] = BlockInput(
                name=name,
                label=input_info.label,
                description=input_info.description,
                type=(
                    input_info.data_type.__name__
                    if hasattr(input_info.data_type, "__name__")
                    else str(input_info.data_type)
                ),
                required=True,  # 假设所有输入都是必需的
                default=input_info.default if hasattr(input_info, "default") else None,
            )

        for name, output_info in getattr(block_type, "outputs", {}).items():
            outputs[name] = BlockOutput(
                name=name,
                label=output_info.label,
                description=output_info.description,
                type=(
                    output_info.data_type.__name__
                    if hasattr(output_info.data_type, "__name__")
                    else str(output_info.data_type)
                ),
            )
        # 内置方法不属于参数（Block 的 __init__ 方法）
        builtin_params = self.get_builtin_params()

        # 获取 __init__ 方法的参数作为配置
        sig = signature(block_type.__init__)
        for param in sig.parameters.values():
            if param.name == "self":
                continue

            if param.name in builtin_params:
                continue

            block_config = extract_block_param(param)

            configs[param.name] = block_config
        return inputs, outputs, configs

    def get_builtin_params(self) -> List[str]:
        """获取内置参数"""
        sig = signature(Block.__init__)
        return [param.name for param in sig.parameters.values()]
