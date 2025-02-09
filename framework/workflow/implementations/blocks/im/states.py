import asyncio
from typing import Any, Dict, Optional
from framework.im.adapter import EditStateAdapter, IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output

# Toggle edit state
class ToggleEditState(Block):
    name = "toggle_edit_state"
    inputs = {"msg": Input("msg", IMMessage, "Input message")}
    outputs = {}
    container: DependencyContainer

    def __init__(self, is_editing: bool):
        self.is_editing = is_editing

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        im_adapter = self.container.resolve(IMAdapter)
        if isinstance(im_adapter, EditStateAdapter):
            loop: asyncio.AbstractEventLoop = self.container.resolve(asyncio.AbstractEventLoop)
            loop.create_task(im_adapter.set_chat_editing_state(msg.sender, self.is_editing))
        return {}