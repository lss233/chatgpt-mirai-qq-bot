from typing import Dict, Any
from framework.im.message import IMMessage, TextMessage
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output
from framework.memory.memory_manager import MemoryManager
from framework.memory.registry import ScopeRegistry

class ClearMemory(Block):
    """Block for clearing conversation memory"""
    
    def __init__(self, container: DependencyContainer, scope_type: str = 'member'):
        inputs = {"msg": Input("msg", IMMessage, "Input message")}
        outputs = {"response": Output("response", IMMessage, "Response message")}
        super().__init__("clear_memory", inputs, outputs)
        
        self.memory_manager = container.resolve(MemoryManager)
        
        # Get scope instance
        scope_registry = container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(scope_type)

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        # Clear memory using the manager's method
        self.memory_manager.clear_memory(self.scope, msg.sender)
        return {"response": IMMessage(sender=msg.sender, message_elements=[TextMessage("已清空当前对话的记忆。")])} 