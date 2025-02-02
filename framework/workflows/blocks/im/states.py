import asyncio
from typing import Any, Dict
from framework.im.adapter import EditStateAdapter, IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow_executor.block import Block
from framework.workflow_executor.input_output import Input, Output

# Toggle edit state
class ToggleEditState(Block):
    def __init__(self, container: DependencyContainer, is_editing: bool):
        inputs = {"msg": Input("msg", IMMessage, "Input message")}
        outputs = {}
        super().__init__("toggle_edit_state", inputs, outputs)
        self.container = container
        self.is_editing = is_editing
    
    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        im_adapter = self.container.resolve(IMAdapter)
        if isinstance(im_adapter, EditStateAdapter):
            loop: asyncio.AbstractEventLoop = self.container.resolve(asyncio.AbstractEventLoop)
            loop.create_task(im_adapter.set_chat_editing_state(msg.sender, self.is_editing))
        return {}