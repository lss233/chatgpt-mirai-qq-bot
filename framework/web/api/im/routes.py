import asyncio
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
    registry: IMRegistry = g.container.resolve(IMRegistry)
    types = list(registry.get_all_adapters().keys())
    return IMAdapterTypes(types=types).model_dump()

@im_bp.route('/adapters', methods=['GET'])
@require_auth
async def list_adapters():
    """获取所有已配置的适配器"""
    config = g.container.resolve(GlobalConfig)
    manager = g.container.resolve(IMManager)
    
    adapters = []
    for im in config.ims:
        is_running = manager.is_adapter_running(im.name)
        configs = im.config
        adapters.append(IMAdapterStatus(
            name=im.name,
            adapter=im.adapter,
            is_running=is_running,
            config=configs
        ))
    
    return IMAdapterList(adapters=adapters).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['GET'])
@require_auth
async def get_adapter(adapter_id: str):
    """获取特定适配器的信息"""
    manager: IMManager = g.container.resolve(IMManager)
    
    # 查找适配器类型
    if not manager.has_adapter(adapter_id):
        return jsonify({"error": "Adapter not found"}), 404
    
    adapter_config = manager.get_adapter_config(adapter_id)
    return IMAdapterResponse(adapter=IMAdapterStatus(
        name=adapter_id,
        adapter=adapter_config.adapter,
        is_running=manager.is_adapter_running(adapter_id),
        config=adapter_config.config

    )).model_dump()

@im_bp.route('/adapters', methods=['POST'])
@require_auth
async def create_adapter():
    """创建新的适配器"""
    data = await request.get_json()
    adapter_config = IMAdapterConfig(**data)
    
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    registry: IMRegistry = g.container.resolve(IMRegistry)
    manager: IMManager = g.container.resolve(IMManager)

    # 检查适配器类型是否存在
    if adapter_config.adapter not in registry.get_all_adapters():
        return jsonify({"error": "Invalid adapter type"}), 400
    
    # 检查ID是否已存在
    if manager.has_adapter(adapter_config.name):
        return jsonify({"error": "Adapter ID already exists"}), 400
    
    # 更新配置
    config.ims.append(adapter_config)
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return IMAdapterResponse(adapter=IMAdapterStatus(
        name=adapter_config.name,
        adapter=adapter_config.adapter,
        is_running=False,
        config=adapter_config.config
    )).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['PUT'])
@require_auth
async def update_adapter(adapter_id: str):
    """更新适配器配置"""
    data = await request.get_json()
    adapter_config = IMAdapterConfig(**data)
    
    if adapter_id != adapter_config.name:
        return jsonify({"error": "Adapter ID mismatch"}), 400
    
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: IMManager = g.container.resolve(IMManager)
    loop = asyncio.get_event_loop()

    # 检查适配器是否存在
    if not manager.has_adapter(adapter_id):
        return jsonify({"error": "Adapter not found"}), 404
    
    # 更新配置
    manager.update_adapter_config(adapter_id, adapter_config.config)
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    # 如果适配器正在运行，需要重启
    is_running = manager.is_adapter_running(adapter_id)
    if is_running:
        await manager.stop_adapter(adapter_id, loop)
        await manager.start_adapter(adapter_id, loop)

    return IMAdapterResponse(adapter=IMAdapterStatus(
        name=adapter_id,
        adapter=adapter_config.adapter,
        is_running=is_running,
        config=adapter_config.config
    )).model_dump()

@im_bp.route('/adapters/<adapter_id>', methods=['DELETE'])
@require_auth
async def delete_adapter(adapter_id: str):
    """删除适配器"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: IMManager = g.container.resolve(IMManager)
    loop = asyncio.get_event_loop()

    # 先停止适配器
    if manager.is_adapter_running(adapter_id):
        await manager.stop_adapter(adapter_id, loop)

    # 从配置中删除
    manager.delete_adapter(adapter_id)
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return jsonify({"message": "Adapter deleted successfully"})

@im_bp.route('/adapters/<adapter_id>/start', methods=['POST'])
@require_auth
async def start_adapter(adapter_id: str):
    """启动适配器"""
    manager: IMManager = g.container.resolve(IMManager)
    loop = asyncio.get_event_loop()
    
    if manager.is_adapter_running(adapter_id):
        return jsonify({"error": "Adapter is already running"}), 400
    
    try:
        await manager.start_adapter(adapter_id, loop)
        return jsonify({"message": "Adapter started successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@im_bp.route('/adapters/<adapter_id>/stop', methods=['POST'])
@require_auth
async def stop_adapter(adapter_id: str):
    """停止适配器"""
    manager: IMManager = g.container.resolve(IMManager)
    loop = asyncio.get_event_loop()

    if not manager.is_adapter_running(adapter_id):
        return jsonify({"error": "Adapter is not running"}), 400
    
    try:
        await manager.stop_adapter(adapter_id, loop)
        return jsonify({"message": "Adapter stopped successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 