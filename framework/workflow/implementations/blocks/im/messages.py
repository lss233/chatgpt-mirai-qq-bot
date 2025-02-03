import asyncio
from typing import Any, Dict, Optional
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output


class GetIMMessage(Block):
    """获取 IM 消息"""
    def __init__(self, container: DependencyContainer):
        outputs = {"msg": Output("msg", IMMessage, "Input message")}
        super().__init__("msg_input", {}, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        msg = self.container.resolve(IMMessage)
        return {"msg": msg}

class SendIMMessage(Block):
    """发送 IM 消息"""
    def __init__(self, container: DependencyContainer):
        inputs = {"msg": Input("msg", IMMessage, "Message to send")}
        super().__init__("msg_sender", inputs, {})
        self.container = container

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        src_msg = self.container.resolve(IMMessage)
        adapter = self.container.resolve(IMAdapter)
        loop: asyncio.AbstractEventLoop = self.container.resolve(asyncio.AbstractEventLoop)
        loop.create_task(adapter.send_message(msg, src_msg.sender))
        # return {"ok": True}
