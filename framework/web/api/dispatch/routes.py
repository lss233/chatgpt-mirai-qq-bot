from quart import Blueprint, request, jsonify, g
from framework.config.config_loader import ConfigLoader
from framework.config.global_config import GlobalConfig
from framework.workflow.core.dispatch import DispatchRuleRegistry
from framework.workflow.core.workflow import WorkflowRegistry
from framework.workflow.core.dispatch.rule import CombinedDispatchRule, DispatchRule
from ...auth.middleware import require_auth
from .models import (
    DispatchRuleResponse, DispatchRuleList
)

dispatch_bp = Blueprint('dispatch', __name__)

@dispatch_bp.route('/rules', methods=['GET'])
@require_auth
async def list_rules():
    """获取所有调度规则"""
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    rules = registry.get_all_rules()
    rules.sort(key=lambda x: x.priority, reverse=True)
    rules = [rule.model_dump() for rule in rules]
    return DispatchRuleList(rules=rules).model_dump()

@dispatch_bp.route('/rules/<rule_id>', methods=['GET'])
@require_auth
async def get_rule(rule_id: str):
    """获取特定调度规则的信息"""
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    
    rule = registry.get_rule(rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    
    return DispatchRuleResponse(rule=rule).model_dump()

@dispatch_bp.route('/rules', methods=['POST'])
@require_auth
async def create_rule():
    """创建新的调度规则"""
    data = await request.get_json()
    rule_data = CombinedDispatchRule(**data)
    
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    workflow_registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    # 检查规则ID是否已存在
    if registry.get_rule(rule_data.rule_id):
        return jsonify({"error": "Rule ID already exists"}), 400
    
    # 检查工作流是否存在
    if not workflow_registry.get(rule_data.workflow_id):
        return jsonify({"error": "Workflow not found"}), 400
    
    try:
        # 创建规则
        rule = registry.create_rule(rule_data)
        
        # 保存规则
        registry.save_rules()
        
        return DispatchRuleResponse(rule=rule).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@dispatch_bp.route('/rules/<rule_id>', methods=['PUT'])
@require_auth
async def update_rule(rule_id: str):
    """更新调度规则"""
    data = await request.get_json()
    rule_data = CombinedDispatchRule(**data)
    
    if rule_id != rule_data.rule_id:
        return jsonify({"error": "Rule ID mismatch"}), 400
    
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    workflow_registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)
    
    # 检查规则是否存在
    if not registry.get_rule(rule_id):
        return jsonify({"error": "Rule not found"}), 404
    
    # 检查工作流是否存在
    if not workflow_registry.get(rule_data.workflow_id):
        return jsonify({"error": "Workflow not found"}), 400
    
    try:
        # 更新规则
        rule = registry.update_rule(rule_id, rule_data)
        
        # 保存规则
        registry.save_rules()
        return DispatchRuleResponse(rule=rule).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@dispatch_bp.route('/rules/<rule_id>', methods=['DELETE'])
@require_auth
async def delete_rule(rule_id: str):
    """删除调度规则"""
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    
    # 检查规则是否存在
    if not registry.get_rule(rule_id):
        return jsonify({"error": "Rule not found"}), 404
    
    # 删除规则
    registry.delete_rule(rule_id)
    
    # 保存规则
    registry.save_rules()
    
    return jsonify({"message": "Rule deleted successfully"})

@dispatch_bp.route('/rules/<rule_id>/enable', methods=['POST'])
@require_auth
async def enable_rule(rule_id: str):
    """启用调度规则"""
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    
    rule = registry.get_rule(rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    
    if rule.enabled:
        return jsonify({"error": "Rule is already enabled"}), 400
    
    # 启用规则
    registry.enable_rule(rule_id)
    
    # 保存规则
    registry.save_rules()
    
    return jsonify({"message": "Rule enabled successfully"})

@dispatch_bp.route('/rules/<rule_id>/disable', methods=['POST'])
@require_auth
async def disable_rule(rule_id: str):
    """禁用调度规则"""
    registry: DispatchRuleRegistry = g.container.resolve(DispatchRuleRegistry)
    
    rule = registry.get_rule(rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    
    if not rule.enabled:
        return jsonify({"error": "Rule is already disabled"}), 400
    
    # 禁用规则
    registry.disable_rule(rule_id)
    
    # 保存规则
    registry.save_rules()
    
    return jsonify({"message": "Rule disabled successfully"})

@dispatch_bp.route('/types', methods=['GET'])
@require_auth
async def get_rule_types():
    """获取所有可用的规则类型"""
    return jsonify({
        'types': list(DispatchRule.rule_types.keys())
    })

@dispatch_bp.route('/types/<rule_type>/config-schema', methods=['GET'])
@require_auth
async def get_rule_config_schema(rule_type: str):
    """获取指定规则类型的配置字段模式"""
    try:
        if rule_type not in DispatchRule.rule_types:
            return jsonify({"error": "Invalid rule type"}), 404
        
        rule_class = DispatchRule.rule_types[rule_type]
        config_class = rule_class.config_class
        schema = config_class.model_json_schema()
        return jsonify({
            'configSchema': schema
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500 