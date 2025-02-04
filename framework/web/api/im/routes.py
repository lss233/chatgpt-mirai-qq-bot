from quart import Blueprint, request, jsonify, g
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from ...auth.middleware import require_auth
from .models import (
    IMAdapterConfig, IMAdapterStatus, IMAdapterList,
    IMAdapterResponse, IMAdapterTypes
)

im_bp = Blueprint('im', __name__)

@im_bp.route('/types', methods=['GET'])
@require_auth
async def get_adapter_types():
    """获取所有可用的适配器类型"""
    registry = g.container.resolve(IMRegistry)
    types = list(registry.get_all_adapters().keys())
    return IMAdapterTypes(types=types).model_dump()

@im_bp.route('/adapters', methods=['GET'])
@require_auth
async def list_adapters():
    """获取所有已配置的适配器"""
    config = g.container.resolve(GlobalConfig)
    manager = g.container.resolve(IMManager)
    
    adapters = []
    for adapter_type, adapter_ids in config.ims.enable.items():
        for adapter_id in adapter_ids:
            is_running = manager.is_adapter_running(adapter_id)
            configs = config.ims.configs.get(adapter_id, {})
            adapters.append(IMAdapterStatus(
                adapter_id=adapter_id,
                adapter_type=adapter_type,
                is_running=is_running,
                configs=configs
            ))
    
    return IMAdapterList(adapters=adapters).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['GET'])
@require_auth
async def get_adapter(adapter_id: str):
    """获取特定适配器的信息"""
    config = g.container.resolve(GlobalConfig)
    manager = g.container.resolve(IMManager)
    
    # 查找适配器类型
    adapter_type = None
    for type_, ids in config.ims.enable.items():
        if adapter_id in ids:
            adapter_type = type_
            break
    
    if not adapter_type:
        return jsonify({"error": "Adapter not found"}), 404
    
    is_running = manager.is_adapter_running(adapter_id)
    configs = config.ims.configs.get(adapter_id, {})
    
    return IMAdapterResponse(adapter=IMAdapterStatus(
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        is_running=is_running,
        configs=configs
    )).model_dump()

@im_bp.route('/adapters', methods=['POST'])
@require_auth
async def create_adapter():
    """创建新的适配器"""
    data = await request.get_json()
    adapter_config = IMAdapterConfig(**data)
    
    config = g.container.resolve(GlobalConfig)
    registry = g.container.resolve(IMRegistry)
    
    # 检查适配器类型是否存在
    if adapter_config.adapter_type not in registry.get_all_adapters():
        return jsonify({"error": "Invalid adapter type"}), 400
    
    # 检查ID是否已存在
    for ids in config.ims.enable.values():
        if adapter_config.adapter_id in ids:
            return jsonify({"error": "Adapter ID already exists"}), 400
    
    # 更新配置
    if adapter_config.adapter_type not in config.ims.enable:
        config.ims.enable[adapter_config.adapter_type] = []
    config.ims.enable[adapter_config.adapter_type].append(adapter_config.adapter_id)
    config.ims.configs[adapter_config.adapter_id] = adapter_config.configs
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return IMAdapterResponse(adapter=IMAdapterStatus(
        adapter_id=adapter_config.adapter_id,
        adapter_type=adapter_config.adapter_type,
        is_running=False,
        configs=adapter_config.configs
    )).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['PUT'])
@require_auth
async def update_adapter(adapter_id: str):
    """更新适配器配置"""
    data = await request.get_json()
    adapter_config = IMAdapterConfig(**data)
    
    if adapter_id != adapter_config.adapter_id:
        return jsonify({"error": "Adapter ID mismatch"}), 400
    
    config = g.container.resolve(GlobalConfig)
    manager = g.container.resolve(IMManager)
    
    # 检查适配器是否存在
    found = False
    for type_, ids in config.ims.enable.items():
        if adapter_id in ids:
            # 如果类型改变，需要移动到新的类型下
            if type_ != adapter_config.adapter_type:
                config.ims.enable[type_].remove(adapter_id)
                if adapter_config.adapter_type not in config.ims.enable:
                    config.ims.enable[adapter_config.adapter_type] = []
                config.ims.enable[adapter_config.adapter_type].append(adapter_id)
            found = True
            break
    
    if not found:
        return jsonify({"error": "Adapter not found"}), 404
    
    # 更新配置
    config.ims.configs[adapter_id] = adapter_config.configs
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    # 如果适配器正在运行，需要重启
    is_running = manager.is_adapter_running(adapter_id)
    if is_running:
        await manager.stop_adapter(adapter_id)
        await manager.start_adapter(adapter_id)
    
    return IMAdapterResponse(adapter=IMAdapterStatus(
        adapter_id=adapter_id,
        adapter_type=adapter_config.adapter_type,
        is_running=is_running,
        configs=adapter_config.configs
    )).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['DELETE'])
@require_auth
async def delete_adapter(adapter_id: str):
    """删除适配器"""
    config = g.container.resolve(GlobalConfig)
    manager = g.container.resolve(IMManager)
    
    # 先停止适配器
    if manager.is_adapter_running(adapter_id):
        await manager.stop_adapter(adapter_id)
    
    # 从配置中删除
    for type_, ids in config.ims.enable.items():
        if adapter_id in ids:
            config.ims.enable[type_].remove(adapter_id)
            if adapter_id in config.ims.configs:
                del config.ims.configs[adapter_id]
            break
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return jsonify({"message": "Adapter deleted successfully"})

@im_bp.route('/adapters/<adapter_id>/start', methods=['POST'])
@require_auth
async def start_adapter(adapter_id: str):
    """启动适配器"""
    manager = g.container.resolve(IMManager)
    
    if manager.is_adapter_running(adapter_id):
        return jsonify({"error": "Adapter is already running"}), 400
    
    try:
        await manager.start_adapter(adapter_id)
        return jsonify({"message": "Adapter started successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@im_bp.route('/adapters/<adapter_id>/stop', methods=['POST'])
@require_auth
async def stop_adapter(adapter_id: str):
    """停止适配器"""
    manager = g.container.resolve(IMManager)
    
    if not manager.is_adapter_running(adapter_id):
        return jsonify({"error": "Adapter is not running"}), 400
    
    try:
        await manager.stop_adapter(adapter_id)
        return jsonify({"message": "Adapter stopped successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 