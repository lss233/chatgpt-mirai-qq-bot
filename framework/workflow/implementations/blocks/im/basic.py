import asyncio
from typing import Any, Dict, Optional
from framework.im.adapter import IMAdapter
from framework.im.manager import IMManager
from framework.im.message import IMMessage
from framework.im.sender import ChatSender
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output


class ExtractChatSender(Block):
    """提取消息发送者"""
    name = "extract_chat_sender"
    container: DependencyContainer
    inputs = {"msg": Input("msg", "IM 消息", IMMessage, "IM 消息")}
    outputs = {"sender": Output("sender", "消息发送者", ChatSender, "消息发送者")}
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        msg = self.container.resolve(IMMessage)
        return {"sender": msg.sender}
