from typing import Any, Dict, List
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output
from framework.ioc.container import DependencyContainer
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry
from framework.im.message import IMMessage, TextMessage

class GenerateHelp(Block):
    """生成帮助信息 block"""
    
    def __init__(self, container: DependencyContainer):
        inputs = {}  # 不需要输入
        outputs = {
            "response": Output("response", IMMessage, "Help message")
        }
        super().__init__("generate_help", inputs, outputs)
        self.container = container
        
    def execute(self) -> Dict[str, Any]:
        # 从容器获取调度规则注册表
        registry = self.container.resolve(DispatchRuleRegistry)
        rules = registry.get_active_rules()
        
        # 按类别组织命令
        commands = {}
        for rule in rules:
            if not hasattr(rule, 'description'):
                continue
                
            # 从 workflow 名称获取类别
            category = rule.workflow_factory.__class__.__name__.replace('WorkflowFactory', '').lower()
            if category not in commands:
                commands[category] = []
                
            # 获取命令格式
            if hasattr(rule, 'prefix'):
                cmd_format = rule.prefix
            elif hasattr(rule, 'keywords'):
                cmd_format = f"[{' | '.join(rule.keywords)}]"
            elif hasattr(rule, 'pattern'):
                cmd_format = f"正则: {rule.pattern}"
            else:
                continue
                
            commands[category].append({
                'format': cmd_format,
                'description': rule.description
            })
            
        # 生成帮助文本
        help_text = "🤖 机器人命令帮助\n\n"
        
        for category, cmds in commands.items():
            help_text += f"📑 {category.upper()}\n"
            for cmd in cmds:
                help_text += f"  {cmd['format']}\n    └─ {cmd['description']}\n"
            help_text += "\n"
            
        return {
            "response": IMMessage(
                sender="<@bot>",
                message_elements=[TextMessage(help_text)]
            )
        } 