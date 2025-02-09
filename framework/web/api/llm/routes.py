from quart import Blueprint, request, jsonify, g
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.ioc.container import DependencyContainer
from framework.llm.llm_manager import LLMManager
from framework.llm.llm_registry import LLMBackendRegistry
from framework.web.api.llm.models import (
    LLMBackendInfo,
    LLMBackendList,
    LLMBackendResponse,
    LLMBackendListResponse,
    LLMBackendCreateRequest,
    LLMBackendUpdateRequest,
    LLMAdapterTypes,
    LLMAdapterConfigSchema
)
from ...auth.middleware import require_auth

llm_bp = Blueprint('llm', __name__)

@llm_bp.route('/types', methods=['GET'])
@require_auth
async def get_adapter_types():
    """获取所有可用的适配器类型"""
    registry: LLMBackendRegistry = g.container.resolve(LLMBackendRegistry)
    return LLMAdapterTypes(types=registry.get_adapter_types()).model_dump()

@llm_bp.route('/backends', methods=['GET'])
@require_auth
async def list_backends():
    """获取所有后端列表"""
    try:
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        backends = []
        for backend in config.llms.api_backends:
            backends.append(LLMBackendInfo(
                name=backend.name,
                adapter=backend.adapter,
                config=backend.config,
                enable=backend.enable,
                models=backend.models
            ))
        return LLMBackendListResponse(
            data=LLMBackendList(backends=backends)
        ).model_dump()
    except Exception as e:
        return LLMBackendListResponse(error=str(e)).model_dump()

@llm_bp.route('/backends/<backend_name>', methods=['GET'])
@require_auth
async def get_backend(backend_name: str):
    """获取指定后端信息"""
    try:
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        backend = next((b for b in config.llms.api_backends if b.name == backend_name), None)
        if not backend:
            return jsonify({"error": f"Backend {backend_name} not found"}), 404
        
        return LLMBackendResponse(
            data=LLMBackendInfo(
                name=backend.name,
                adapter=backend.adapter,
                config=backend.config,
                enable=backend.enable,
                models=backend.models
            )
        ).model_dump()
    except Exception as e:
        return LLMBackendResponse(error=str(e)).model_dump()

@llm_bp.route('/backends', methods=['POST'])
@require_auth
async def create_backend():
    """创建新的后端"""
    try:
        data = await request.get_json()
        request_data = LLMBackendCreateRequest(**data)
        
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        manager: LLMManager = g.container.resolve(LLMManager)
        
        # 检查后端名称是否已存在
        if any(b.name == request_data.name for b in config.llms.api_backends):
            return jsonify({"error": f"Backend {request_data.name} already exists"}), 400
        
        # 创建新的后端配置
        backend = LLMBackendInfo(
            name=request_data.name,
            adapter=request_data.adapter,
            config=request_data.config,
            enable=request_data.enable,
            models=request_data.models
        )
        
        # 添加到配置中
        config.llms.api_backends.append(backend)
        
        # 如果启用则加载后端
        if backend.enable:
            manager.load_backend(backend.name)
        
        ConfigLoader.save_config_with_backup("config.yaml", config)
        return LLMBackendResponse(data=backend).model_dump()
    except Exception as e:
        return LLMBackendResponse(error=str(e)).model_dump()

@llm_bp.route('/backends/<backend_name>', methods=['PUT'])
@require_auth
async def update_backend(backend_name: str):
    """更新指定后端"""
    try:
        data = await request.get_json()
        request_data = LLMBackendUpdateRequest(**data)
        
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        manager: LLMManager = g.container.resolve(LLMManager)
        
        # 查找要更新的后端
        backend_index = next((i for i, b in enumerate(config.llms.api_backends) if b.name == backend_name), -1)
        if backend_index == -1:
            return jsonify({"error": f"Backend {backend_name} not found"}), 404
        
        # 创建更新后的后端配置
        updated_backend = LLMBackendInfo(
            name=request_data.name,
            adapter=request_data.adapter,
            config=request_data.config,
            enable=request_data.enable,
            models=request_data.models
        )
        
        # 如果原后端已启用，先卸载
        if config.llms.api_backends[backend_index].enable:
            await manager.unload_backend(backend_name)
        
        # 更新配置
        config.llms.api_backends[backend_index] = updated_backend
        
        # 如果新配置启用则加载后端
        if updated_backend.enable:
            manager.load_backend(updated_backend.name)
        ConfigLoader.save_config_with_backup("config.yaml", config)
        return LLMBackendResponse(data=updated_backend).model_dump()
    except Exception as e:
        return LLMBackendResponse(error=str(e)).model_dump()

@llm_bp.route('/backends/<backend_name>', methods=['DELETE'])
@require_auth
async def delete_backend(backend_name: str):
    """删除指定后端"""
    try:
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        manager: LLMManager = g.container.resolve(LLMManager)
        
        # 查找要删除的后端
        backend_index = next((i for i, b in enumerate(config.llms.api_backends) if b.name == backend_name), -1)
        if backend_index == -1:
            return jsonify({"error": f"Backend {backend_name} not found"}), 404
        
        # 如果后端已启用，先卸载
        if config.llms.api_backends[backend_index].enable:
            await manager.unload_backend(backend_name)
        
        # 从配置中删除
        deleted_backend = config.llms.api_backends.pop(backend_index)
        
        ConfigLoader.save_config_with_backup("config.yaml", config)
        
        return LLMBackendResponse(data=LLMBackendInfo(
            name=deleted_backend.name,
            adapter=deleted_backend.adapter,
            config=deleted_backend.config,
            enable=deleted_backend.enable,
            models=deleted_backend.models
        )).model_dump()
    except Exception as e:
        return LLMBackendResponse(error=str(e)).model_dump()

@llm_bp.route('/types/<adapter_type>/config-schema', methods=['GET'])
@require_auth
async def get_adapter_config_schema(adapter_type: str):
    """获取指定适配器类型的配置字段模式"""
    try:
        registry: LLMBackendRegistry = g.container.resolve(LLMBackendRegistry)
        config_class = registry.get_config_class(adapter_type)
        if not config_class:
            return jsonify({"error": f"Adapter type {adapter_type} not found"}), 404
        
        schema = config_class.model_json_schema()
        return LLMAdapterConfigSchema(configSchema=schema).model_dump()
    except Exception as e:
        return LLMAdapterConfigSchema(error=str(e)).model_dump() 