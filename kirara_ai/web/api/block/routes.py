from quart import Blueprint, g, jsonify

from kirara_ai.workflow.core.block import BlockRegistry

from ...auth.middleware import require_auth
from .models import BlockConfig, BlockInput, BlockOutput, BlockType, BlockTypeList, BlockTypeResponse

block_bp = Blueprint("block", __name__)


@block_bp.route("/types", methods=["GET"])
@require_auth
async def list_block_types():
    """获取所有可用的Block类型"""
    registry: BlockRegistry = g.container.resolve(BlockRegistry)

    types = []
    for block_type in registry.get_all_types():
        inputs, outputs, configs = registry.extract_block_info(block_type)
        type_name = registry.get_block_type_name(block_type)

        for config in configs.values():
            if config.has_options:
                config.options = config.options_provider(g.container, block_type)

        block_type_info = BlockType(
            type_name=type_name,
                name=block_type.name,
                label=registry.get_localized_name(type_name),
                description=getattr(block_type, "description", ""),
                inputs=inputs.values(),
                outputs=outputs.values(),
                configs=configs.values(),
        )
        types.append(block_type_info)

    return BlockTypeList(types=types).model_dump()


@block_bp.route("/types/<type_name>", methods=["GET"])
@require_auth
async def get_block_type(type_name: str):
    """获取特定Block类型的详细信息"""
    registry: BlockRegistry = g.container.resolve(BlockRegistry)

    block_type = registry.get(type_name)
    if not block_type:
        return jsonify({"error": "Block type not found"}), 404

    # 获取Block类的输入输出定义
    inputs = []
    for name, info in block_type.get_inputs().items():
        inputs.append(
            BlockInput(
                name=name,
                label=registry.get_localized_name(name),
                description=info.get("description", ""),
                type=info.get("type", "any"),
                required=info.get("required", True),
                default=info.get("default"),
            )
        )

    outputs = []
    for name, info in block_type.get_outputs().items():
        outputs.append(
            BlockOutput(
                name=name,
                description=info.get("description", ""),
                type=info.get("type", "any"),
            )
        )

    configs = []
    for name, info in block_type.get_configs().items():
        if info.has_options:
            info.options = info.options_provider(g.container, block_type)
        configs.append(
            BlockConfig(
                name=name,
                description=info.get("description", ""),
                type=info.get("type", "any"),
                required=info.get("required", True),
                default=info.get("default"),
            )
        )

    return BlockTypeResponse(
        type=BlockType(
            type_name=registry.get_block_type_name(block_type),
            name=block_type.name,
            label=registry.get_localized_name(block_type.name),
            description=block_type.description,
            inputs=inputs,
            outputs=outputs,
            configs=configs,
        )
    ).model_dump()


@block_bp.route("/types/compatibility", methods=["GET"])
@require_auth
async def get_type_compatibility():
    """获取所有类型的兼容性映射"""
    registry: BlockRegistry = g.container.resolve(BlockRegistry)
    return jsonify(registry.get_type_compatibility_map())
