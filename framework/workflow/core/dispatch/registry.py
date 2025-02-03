from typing import List
from framework.workflow.core.dispatch.rule import DispatchRule, PrefixMatchRule, KeywordMatchRule, RegexMatchRule
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
        self.rules: List[DispatchRule] = []
        self.logger = get_logger("DispatchRuleRegistry")
        

    def register(self, rule: DispatchRule):
        """注册一个调度规则"""
        self.rules.append(rule)
        self.logger.info(f"Registered dispatch rule: {rule}")
        
    def load_rules(self, rules_dir: str = "data/dispatch_rules"):
        """从指定目录加载所有调度规则"""
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
                    rule = self._create_rule(rule_data)
                    if rule:
                        self.register(rule)
                        
            except Exception as e:
                self.logger.error(f"Failed to load rules from {file_path}: {str(e)}")
                
    def _create_rule(self, rule_data: dict) -> DispatchRule:
        """从规则数据创建调度规则实例"""
        rule_type = rule_data.get('type')
        workflow_name = rule_data.get('workflow')
        description = rule_data.get('description')

        if not rule_type or not workflow_name:
            raise ValueError("Rule must specify 'type' and 'workflow'")
            
        # 获取工作流构建器
        workflow_builder = self.workflow_registry.get(workflow_name)
        if not workflow_builder:
            raise ValueError(f"Workflow {workflow_name} not found")

        # 规则类型到构造函数的映射
        rule_constructors = {
            'prefix': (PrefixMatchRule, 'prefix', str),
            'keyword': (KeywordMatchRule, 'keywords', list),
            'regex': (RegexMatchRule, 'pattern', str)
        }

        if rule_type not in rule_constructors:
            raise ValueError(f"Unknown rule type: {rule_type}")

        # 获取构造信息
        constructor, param_name, param_type = rule_constructors[rule_type]
        param_value = rule_data.get(param_name)

        # 验证参数
        if not param_value or not isinstance(param_value, param_type):
            raise ValueError(f"{rule_type} rule must specify '{param_name}' as {param_type.__name__}")

        # 创建规则实例
        rule = constructor(param_value, workflow_builder)
        
        # 如果有描述信息,添加到规则实例
        if description:
            rule.description = description

        return rule
            
    def get_rules(self) -> List[DispatchRule]:
        """获取所有已注册的规则"""
        return self.rules.copy() 