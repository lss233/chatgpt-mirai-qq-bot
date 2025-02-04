from quart import Blueprint, request, jsonify, g
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.llm.llm_registry import LLMBackendRegistry
from framework.llm.llm_manager import LLMManager
from ...auth.middleware import require_auth
from .models import (
    LLMBackendConfig, LLMBackendStatus, LLMBackendList,
    LLMBackendResponse, LLMAdapterTypes
)

llm_bp = Blueprint('llm', __name__)

@llm_bp.route('/types', methods=['GET'])
@require_auth
async def get_adapter_types():
    """获取所有可用的LLM适配器类型"""
    registry = g.container.resolve(LLMBackendRegistry)
    types = list(registry.get_all_adapters().keys())
    return LLMAdapterTypes(types=types).model_dump()

@llm_bp.route('/backends', methods=['GET'])
@require_auth
async def list_backends():
    """获取所有已配置的LLM后端"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)
    

    backends = []
    for backend_id, backend_config in config.llms.backends.items():
        is_available = manager.is_backend_available(backend_id)
        backends.append(LLMBackendStatus(
            backend_id=backend_id,
            adapter=backend_config.adapter,
            enable=backend_config.enable,
            configs=backend_config.configs,
            models=backend_config.models,
            is_available=is_available
        ))
    
    return LLMBackendList(backends=backends).model_dump()

@llm_bp.route('/backends/<backend_id>', methods=['GET'])
@require_auth
async def get_backend(backend_id: str):
    """获取特定LLM后端的信息"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)

    if backend_id not in config.llms.backends:
        return jsonify({"error": "Backend not found"}), 404
    
    backend_config = config.llms.backends[backend_id]
    is_available = manager.is_backend_available(backend_id)
    
    return LLMBackendResponse(backend=LLMBackendStatus(
        backend_id=backend_id,
        adapter=backend_config.adapter,
        enable=backend_config.enable,
        configs=backend_config.configs,
        models=backend_config.models,
        is_available=is_available
    )).model_dump()

@llm_bp.route('/backends', methods=['POST'])
@require_auth
async def create_backend():
    """创建新的LLM后端"""
    data = await request.get_json()
    backend_config = LLMBackendConfig(**data)
    
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    registry = g.container.resolve(LLMBackendRegistry)
    
    # 检查适配器类型是否存在
    if backend_config.adapter not in registry.get_all_adapters():
        return jsonify({"error": "Invalid adapter type"}), 400
    
    # 检查ID是否已存在
    if backend_config.backend_id in config.llms.backends:
        return jsonify({"error": "Backend ID already exists"}), 400
    
    # 更新配置
    from framework.llm.llm_registry import LLMBackendConfig as ConfigModel
    config.llms.backends[backend_config.backend_id] = ConfigModel(
        enable=backend_config.enable,
        adapter=backend_config.adapter,
        configs=backend_config.configs,
        models=backend_config.models
    )
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return LLMBackendResponse(backend=LLMBackendStatus(
        backend_id=backend_config.backend_id,
        adapter=backend_config.adapter,
        enable=backend_config.enable,
        configs=backend_config.configs,
        models=backend_config.models,
        is_available=False
    )).model_dump()

@llm_bp.route('/backends/<backend_id>', methods=['PUT'])
@require_auth
async def update_backend(backend_id: str):
    """更新LLM后端配置"""
    data = await request.get_json()
    backend_config = LLMBackendConfig(**data)
    
    if backend_id != backend_config.backend_id:
        return jsonify({"error": "Backend ID mismatch"}), 400
    
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)
    
    if backend_id not in config.llms.backends:
        return jsonify({"error": "Backend not found"}), 404
    
    # 更新配置
    from framework.llm.llm_registry import LLMBackendConfig as ConfigModel
    config.llms.backends[backend_id] = ConfigModel(
        enable=backend_config.enable,
        adapter=backend_config.adapter,
        configs=backend_config.configs,
        models=backend_config.models
    )
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    # 如果后端已启用，需要重新加载
    is_available = manager.is_backend_available(backend_id)
    if backend_config.enable and is_available:
        await manager.reload_backend(backend_id)
    
    return LLMBackendResponse(backend=LLMBackendStatus(
        backend_id=backend_id,
        adapter=backend_config.adapter,
        enable=backend_config.enable,
        configs=backend_config.configs,
        models=backend_config.models,
        is_available=is_available
    )).model_dump()

@llm_bp.route('/backends/<backend_id>', methods=['DELETE'])
@require_auth
async def delete_backend(backend_id: str):
    """删除LLM后端"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)
    
    if backend_id not in config.llms.backends:
        return jsonify({"error": "Backend not found"}), 404
    
    # 如果后端正在运行，先停止它
    if manager.is_backend_available(backend_id):
        await manager.unload_backend(backend_id)
    
    # 从配置中删除
    del config.llms.backends[backend_id]
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    return jsonify({"message": "Backend deleted successfully"})

@llm_bp.route('/backends/<backend_id>/enable', methods=['POST'])
@require_auth
async def enable_backend(backend_id: str):
    """启用LLM后端"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)
    
    if backend_id not in config.llms.backends:
        return jsonify({"error": "Backend not found"}), 404
    
    backend_config = config.llms.backends[backend_id]
    if backend_config.enable:
        return jsonify({"error": "Backend is already enabled"}), 400
    
    # 更新配置
    backend_config.enable = True
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    # 加载后端
    try:
        await manager.load_backend(backend_id)
        return jsonify({"message": "Backend enabled successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@llm_bp.route('/backends/<backend_id>/disable', methods=['POST'])
@require_auth
async def disable_backend(backend_id: str):
    """禁用LLM后端"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    manager: LLMManager = g.container.resolve(LLMManager)
    
    if backend_id not in config.llms.backends:
        return jsonify({"error": "Backend not found"}), 404
    
    backend_config = config.llms.backends[backend_id]
    if not backend_config.enable:
        return jsonify({"error": "Backend is already disabled"}), 400
    
    # 更新配置
    backend_config.enable = False
    
    # 保存配置到文件
    ConfigLoader.save_config_with_backup("config.yaml", config)
    
    # 卸载后端
    try:
        await manager.unload_backend(backend_id)
        return jsonify({"message": "Backend disabled successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 