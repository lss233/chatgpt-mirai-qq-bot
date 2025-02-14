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


class GetIMMessage(Block):
    """获取 IM 消息"""
    name = "msg_input"
    container: DependencyContainer
    outputs = {
        "msg": Output("msg", "IM 消息", IMMessage, "获取 IM 发送的最新一条的消息"),
        "sender": Output("sender", "发送者", ChatSender, "获取 IM 消息的发送者")
        }
        
    def execute(self, **kwargs) -> Dict[str, Any]:
        msg = self.container.resolve(IMMessage)
        return {"msg": msg, "sender": msg.sender}

class SendIMMessage(Block):
    """发送 IM 消息"""
    name = "msg_sender"
    inputs = {"msg": Input("msg", "IM 消息", IMMessage, "要从 IM 发送的消息")}
    outputs = {}
    container: DependencyContainer
    
    def __init__(self, im_name: Optional[str] = None):
        self.im_name = im_name

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        src_msg = self.container.resolve(IMMessage)
        if not self.im_name:
            adapter = self.container.resolve(IMAdapter)
        else:
            adapter = self.container.resolve(IMManager).get_adapter(self.im_name)
        loop: asyncio.AbstractEventLoop = self.container.resolve(asyncio.AbstractEventLoop)
        loop.create_task(adapter.send_message(msg, src_msg.sender))
        # return {"ok": True}