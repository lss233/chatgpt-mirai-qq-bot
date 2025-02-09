from typing import Dict, Any
from framework.im.message import IMMessage, TextMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output
from framework.memory.memory_manager import MemoryManager
from framework.memory.registry import ScopeRegistry

class ClearMemory(Block):
    """Block for clearing conversation memory"""
    name = "clear_memory"
    inputs = {"msg": Input("msg", IMMessage, "Input message")}  
    outputs = {"response": Output("response", IMMessage, "Response message")}
    container: DependencyContainer
    
    def __init__(self, scope_type: str = 'member'):
        self.scope_type = scope_type

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        self.memory_manager = self.container.resolve(MemoryManager)
        
        # Get scope instance
        scope_registry = self.container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(self.scope_type)
        # Clear memory using the manager's method
        self.memory_manager.clear_memory(self.scope, msg.sender)
        return {"response": IMMessage(sender=msg.sender, message_elements=[TextMessage("已清空当前对话的记忆。")])} 