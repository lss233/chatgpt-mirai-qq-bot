from typing import List, Dict, Any, Optional
from framework.workflow.core.dispatch.rule import (
    DispatchRule, RuleConfig, RegexRuleConfig, PrefixRuleConfig, KeywordRuleConfig
)
from framework.workflow.core.workflow.registry import WorkflowRegistry
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
import os
from ruamel.yaml import YAML

class DispatchRuleRegistry:
    """调度规则注册表，管理调度规则的加载和注册"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.workflow_registry = container.resolve(WorkflowRegistry)
        self.rules: Dict[str, DispatchRule] = {}  # 使用字典存储规则，便于查找
        self.logger = get_logger("DispatchRuleRegistry")
        self.rules_dir = "data/dispatch_rules"
        
    def register(self, rule: DispatchRule):
        """注册一个调度规则"""
        if not rule.rule_id:
            raise ValueError("Rule must have an ID")
        self.rules[rule.rule_id] = rule
        self.logger.info(f"Registered dispatch rule: {rule}")
        
    def get_rule(self, rule_id: str) -> Optional[DispatchRule]:
        """获取指定ID的规则"""
        return self.rules.get(rule_id)
    
    def get_all_rules(self) -> List[DispatchRule]:
        """获取所有已注册的规则"""
        return list(self.rules.values())
        
    def get_active_rules(self) -> List[DispatchRule]:
        """获取所有已启用的规则，按优先级降序排序"""
        active_rules = [rule for rule in self.rules.values() if rule.enabled]
        return sorted(active_rules, key=lambda x: x.priority, reverse=True)
        
    def create_rule(self, rule_id: str, name: str, description: str, rule_type: str,
                   workflow_id: str, rule_config: Dict[str, Any], priority: int = 5,
                   enabled: bool = True, metadata: Optional[Dict[str, Any]] = None) -> DispatchRule:
        """创建并注册一个新的规则"""
        # 获取工作流构建器
        workflow_builder = self.workflow_registry.get(workflow_id)
        if not workflow_builder:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        # 获取规则类型
        rule_class = DispatchRule.get_rule_type(rule_type)
        
        # 创建规则配置
        config = rule_class.config_class(**rule_config)
        
        # 创建规则实例
        rule = rule_class.from_config(config, workflow_builder)
        
        # 设置规则属性
        rule.rule_id = rule_id
        rule.name = name
        rule.description = description
        rule.priority = priority
        rule.workflow_id = workflow_id
        rule.enabled = enabled
        rule.metadata = metadata or {}
        
        # 注册规则
        self.register(rule)
        return rule
        
    def update_rule(self, rule_id: str, name: str, description: str, rule_type: str,
                   workflow_id: str, rule_config: Dict[str, Any], priority: int = 5,
                   enabled: bool = True, metadata: Optional[Dict[str, Any]] = None) -> DispatchRule:
        """更新现有规则"""
        if rule_id not in self.rules:
            raise ValueError(f"Rule {rule_id} not found")
            
        # 创建新规则并替换
        rule = self.create_rule(
            rule_id=rule_id,
            name=name,
            description=description,
            rule_type=rule_type,
            workflow_id=workflow_id,
            rule_config=rule_config,
            priority=priority,
            enabled=enabled,
            metadata=metadata
        )
        return rule
        
    def delete_rule(self, rule_id: str):
        """删除规则"""
        if rule_id not in self.rules:
            raise ValueError(f"Rule {rule_id} not found")
        del self.rules[rule_id]
        
    def enable_rule(self, rule_id: str):
        """启用规则"""
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        rule.enabled = True
        
    def disable_rule(self, rule_id: str):
        """禁用规则"""
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        rule.enabled = False
        
    def load_rules(self, rules_dir: Optional[str] = None):
        """从指定目录加载所有调度规则"""
        rules_dir = rules_dir or self.rules_dir
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir)
            
        yaml = YAML(typ='safe')
        
        for file_name in os.listdir(rules_dir):
            if not file_name.endswith('.yaml'):
                continue
                
            file_path = os.path.join(rules_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    rules_data = yaml.load(f)
                    
                if not isinstance(rules_data, list):
                    self.logger.warning(f"Invalid rules file {file_name}, expected list of rules")
                    continue
                    
                for rule_data in rules_data:
                    try:
                        # 获取规则类型
                        rule_type = rule_data['type']
                        rule_class = DispatchRule.get_rule_type(rule_type)
                        
                        # 提取规则配置
                        config_fields = rule_class.config_class.__fields__.keys()
                        rule_config = {k: rule_data[k] for k in config_fields if k in rule_data}
                        
                        rule = self.create_rule(
                            rule_id=rule_data['rule_id'],
                            name=rule_data['name'],
                            description=rule_data.get('description', ''),
                            rule_type=rule_type,
                            workflow_id=rule_data['workflow_id'],
                            rule_config=rule_config,
                            priority=rule_data.get('priority', 5),
                            enabled=rule_data.get('enabled', True),
                            metadata=rule_data.get('metadata', {})
                        )
                        self.logger.info(f"Loaded rule: {rule}")
                    except Exception as e:
                        self.logger.trace(e)
                        self.logger.error(f"Failed to load rule in file {file_path}: {str(e)}")
                        
            except Exception as e:
                self.logger.error(f"Failed to load rules from {file_path}: {str(e)}")
                
    def save_rules(self, rules_dir: Optional[str] = None):
        """保存所有规则到文件"""
        rules_dir = rules_dir or self.rules_dir
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir)
            
        yaml = YAML()
        yaml.default_flow_style = False
        
        # 将规则转换为可序列化的格式
        rules_data = []
        for rule in self.rules.values():
            # 获取基本信息
            rule_data = {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'type': rule.type_name,
                'priority': rule.priority,
                'workflow_id': rule.workflow_id,
                'enabled': rule.enabled,
                'metadata': rule.metadata
            }
            
            # 添加规则配置
            config = rule.get_config()
            rule_data.update(config.dict())
            
            rules_data.append(rule_data)
            
        # 保存到文件
        file_path = os.path.join(rules_dir, 'rules.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(rules_data, f) 