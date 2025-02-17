import random
import re
from typing import Any, Dict

from framework.im.message import IMMessage, TextMessage
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input, Output


class DiceRoll(Block):
    """骰子掷点 block"""

    name = "dice_roll"
    inputs = {
        "message": Input("message", "输入消息", IMMessage, "输入消息包含骰子命令")
    }
    outputs = {
        "response": Output(
            "response", "响应消息", IMMessage, "响应消息包含骰子掷点结果"
        )
    }

    def execute(self, message: IMMessage) -> Dict[str, Any]:
        # 解析命令
        command = message.content
        match = re.match(r"^[.。]roll\s*(\d+)?d(\d+)", command)
        if not match:
            return {
                "response": IMMessage(
                    sender="<@bot>",
                    message_elements=[TextMessage("Invalid dice command")],
                )
            }

        count = int(match.group(1) or "1")  # 默认1个骰子
        sides = int(match.group(2))

        if count > 100:  # 限制骰子数量
            return {
                "response": IMMessage(
                    sender="<@bot>",
                    message_elements=[TextMessage("Too many dice (max 100)")],
                )
            }

        # 掷骰子
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)

        # 生成详细信息
        details = f"🎲 掷出了 {count}d{sides}: {' + '.join(map(str, rolls))}"
        if count > 1:
            details += f" = {total}"

        return {
            "response": IMMessage(
                sender="<@bot>", message_elements=[TextMessage(details)]
            )
        }
