from typing import Any, Dict

from framework.im.message import IMMessage, TextMessage
from framework.im.sender import ChatSender
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block, Output
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry


class GenerateHelp(Block):
    """生成帮助信息 block"""

    name = "generate_help"
    inputs = {}  # 不需要输入
    outputs = {"response": Output("response", "帮助信息", IMMessage, "帮助信息")}
    container: DependencyContainer

    def _format_rule_condition(self, rule_type: str, config: Dict[str, Any]) -> str:
        """格式化单个规则的条件描述"""
        if rule_type == "prefix":
            return f"输入以 {config['prefix']} 开头"
        elif rule_type == "keyword":
            keywords = config.get("keywords", [])
            return f"输入包含 {' 或 '.join(keywords)}"
        elif rule_type == "regex":
            return f"输入匹配正则 {config['pattern']}"
        elif rule_type == "fallback":
            return "任意输入"
        return f"使用 {rule_type} 规则"

    def _format_rule_group(self, group: Dict[str, Any]) -> str:
        """格式化规则组的条件描述"""
        rule_conditions = []
        for rule in group["rules"]:
            rule_conditions.append(
                self._format_rule_condition(rule["type"], rule["config"])
            )

        operator = " 且 " if group["operator"] == "and" else " 或 "
        return operator.join(rule_conditions)

    def execute(self) -> Dict[str, Any]:
        # 从容器获取调度规则注册表
        registry = self.container.resolve(DispatchRuleRegistry)
        rules = registry.get_active_rules()

        # 按类别组织命令
        commands = {}
        for rule in rules:
            # 从 workflow 名称获取类别
            category = rule.workflow_id.split(":")[0].lower()
            if category not in commands:
                commands[category] = []

            # 格式化规则组条件
            conditions = []
            for group in rule.rule_groups:
                conditions.append(self._format_rule_group(group.model_dump()))

            # 组合所有条件（规则组之间是 AND 关系）
            rule_format = " 并且 ".join(f"({condition})" for condition in conditions)

            commands[category].append(
                {
                    "name": rule.name,
                    "format": rule_format,
                    "description": rule.description,
                }
            )

        # 生成帮助文本
        help_text = "🤖 机器人命令帮助\n\n"

        for category, cmds in sorted(commands.items()):
            help_text += f"📑 {category.upper()}\n"
            for cmd in sorted(cmds, key=lambda x: x["name"]):
                help_text += f"🔸 {cmd['name']}\n"
                help_text += f"  触发条件: {cmd['format']}\n"
                if cmd["description"]:
                    help_text += f"  说明: {cmd['description']}\n"
                help_text += "\n"
            help_text += "\n"

        return {
            "response": IMMessage(
                sender=ChatSender.get_bot_sender(),
                message_elements=[TextMessage(help_text)],
            )
        }
