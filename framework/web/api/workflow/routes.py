from quart import Blueprint, request, jsonify, g
from framework.workflow.core.workflow import WorkflowRegistry
from framework.workflow.core.workflow.builder import WorkflowBuilder
from ...auth.middleware import require_auth
from .models import (
    WorkflowDefinition, WorkflowInfo, WorkflowList,
    WorkflowResponse
)
import os

workflow_bp = Blueprint('workflow', __name__)

@workflow_bp.route('', methods=['GET'])
@require_auth
async def list_workflows():
    """获取所有工作流列表"""
    registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    workflows = []
    for workflow_id, builder in registry._workflows.items():
        # 从 workflow_id 解析 group_id
        group_id, wf_id = workflow_id.split(':', 1)
        
        # 创建工作流实例以获取信息
        workflow = builder.build()
        
        workflows.append(WorkflowInfo(
            group_id=group_id,
            workflow_id=wf_id,
            name=workflow.name,
            description=workflow.description if hasattr(workflow, 'description') else '',
            block_count=len(workflow.blocks),
            metadata=workflow.metadata if hasattr(workflow, 'metadata') else None
        ))
        
    return WorkflowList(workflows=workflows).model_dump()

@workflow_bp.route('/<group_id>/<workflow_id>', methods=['GET'])
@require_auth
async def get_workflow(group_id: str, workflow_id: str):
    """获取特定工作流的详细信息"""
    registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    full_id = f"{group_id}:{workflow_id}"
    builder = registry.get(full_id)
    if not builder:
        return jsonify({"error": "Workflow not found"}), 404
        
    # 创建工作流实例
    workflow = builder.build()
    
    # 构建工作流定义
    blocks = []
    for block in workflow.blocks:
        blocks.append({
            'block_id': block.id,
            'type_name': block.__class__.__name__,
            'name': block.name,
            'config': block.config,
            'position': block.position if hasattr(block, 'position') else {'x': 0, 'y': 0}
        })
        
    wires = []
    for wire in workflow.wires:
        wires.append({
            'source_block': wire.source_block.id,
            'source_output': wire.source_output,
            'target_block': wire.target_block.id,
            'target_input': wire.target_input
        })
        
    workflow_def = WorkflowDefinition(
        group_id=group_id,
        workflow_id=workflow_id,
        name=workflow.name,
        description=workflow.description if hasattr(workflow, 'description') else '',
        blocks=blocks,
        wires=wires,
        metadata=workflow.metadata if hasattr(workflow, 'metadata') else None
    )
    
    return WorkflowResponse(workflow=workflow_def).model_dump()

@workflow_bp.route('/<group_id>/<workflow_id>', methods=['POST'])
@require_auth
async def create_workflow(group_id: str, workflow_id: str):
    """创建新的工作流"""
    data = await request.get_json()
    workflow_def = WorkflowDefinition(**data)
    
    registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    # 检查工作流是否已存在
    full_id = f"{group_id}:{workflow_id}"
    if registry.get(full_id):
        return jsonify({"error": "Workflow already exists"}), 400
        
    # 创建工作流构建器
    try:
        # 创建工作流构建器
        builder = WorkflowBuilder(workflow_def.name, g.container)
        
        # 根据定义添加块和连接
        for block_def in workflow_def.blocks:
            block_class = registry.get_block_type(block_def.type_name)
            if not block_class:
                raise ValueError(f"Block type {block_def.type_name} not found")
                
            if not builder.head:
                builder.use(block_class, name=block_def.name, **block_def.config)
            else:
                builder.chain(block_class, name=block_def.name, **block_def.config)
                
        # 添加连接
        for wire in workflow_def.wires:
            source_block = next(b for b in builder.blocks if b.name == wire.source_block)
            target_block = next(b for b in builder.blocks if b.name == wire.target_block)
            builder._connect_blocks(source_block, target_block)
            
        # 保存工作流
        file_path = registry.get_workflow_path(group_id, workflow_id)
        builder.save_to_yaml(file_path)
        
        # 注册工作流
        registry.register(group_id, workflow_id, builder.__class__)
        
        return workflow_def.model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@workflow_bp.route('/<group_id>/<workflow_id>', methods=['PUT'])
@require_auth
async def update_workflow(group_id: str, workflow_id: str):
    """更新现有工作流"""
    data = await request.get_json()
    workflow_def = WorkflowDefinition(**data)
    
    registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    # 检查工作流是否存在
    full_id = f"{group_id}:{workflow_id}"
    if not registry.get(full_id):
        return jsonify({"error": "Workflow not found"}), 404
        
    # 更新工作流
    try:
        # 创建新的工作流构建器
        builder = WorkflowBuilder(workflow_def.name, g.container)
        
        # 根据定义添加块和连接
        for block_def in workflow_def.blocks:
            block_class = registry.get_block_type(block_def.type_name)
            if not block_class:
                raise ValueError(f"Block type {block_def.type_name} not found")
                
            if not builder.head:
                builder.use(block_class, name=block_def.name, **block_def.config)
            else:
                builder.chain(block_class, name=block_def.name, **block_def.config)
                
        # 添加连接
        for wire in workflow_def.wires:
            source_block = next(b for b in builder.blocks if b.name == wire.source_block)
            target_block = next(b for b in builder.blocks if b.name == wire.target_block)
            builder._connect_blocks(source_block, target_block)
            
        # 保存工作流
        file_path = registry.get_workflow_path(group_id, workflow_id)
        builder.save_to_yaml(file_path)
        
        # 更新注册表
        registry.register(group_id, workflow_id, builder.__class__)
        
        return workflow_def.model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@workflow_bp.route('/<group_id>/<workflow_id>', methods=['DELETE'])
@require_auth
async def delete_workflow(group_id: str, workflow_id: str):
    """删除工作流"""
    registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    # 检查工作流是否存在
    full_id = f"{group_id}:{workflow_id}"
    if not registry.get(full_id):
        return jsonify({"error": "Workflow not found"}), 404
        
    try:
        # 从注册表中移除
        registry._workflows.pop(full_id, None)
        
        # 删除文件
        file_path = registry.get_workflow_path(group_id, workflow_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return jsonify({"message": "Workflow deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400 