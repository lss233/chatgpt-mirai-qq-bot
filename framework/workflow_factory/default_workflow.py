import asyncio
from typing import Any, Dict, List
from framework.im.adapter import IMAdapter
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.llm.llm_manager import LLMManager
from framework.workflow_executor.workflow import Wire, Workflow
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.workflow_executor.block import Block
from framework.workflow_executor.input_output import Input, Output

class IMMessageInputBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {}
        outputs = {"message": Output("message", IMMessage, "IM message from container")}
        super().__init__("im_message_input", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        message = self.container.resolve(IMMessage)
        return {"message": message}
    
class MessageConverterBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"message": Input("message", IMMessage, "Input IM message")}
        outputs = {"llm_message": Output("llm_message", List[LLMChatMessage], "Converted LLM message")}
        super().__init__("message_converter", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        im_message = kwargs["message"]
        # Convert IMMessage to string format  for LLM
        llm_message = LLMChatMessage(role='user', content=im_message.content)
        return {"llm_message": [llm_message]}

class LLMChatBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"prompt": Input("prompt", List[LLMChatMessage], "Input prompt for LLM")}
        outputs = {"response": Output("response", LLMChatResponse, "LLM response text")}
        super().__init__("llm_chat", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        prompt = kwargs["prompt"]
        llm_manager: LLMManager = self.container.resolve(LLMManager)
        model_name = 'deepseek-r1'
        adapter = llm_manager.get_llm(model_name)
        req = LLMChatRequest(messages=prompt, model='DeepSeek-R1')
        response = adapter.chat(req)
        return {"response": response}

class MessageSenderBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"message": Input("message", LLMChatResponse, "Response to send")}
        outputs = {"sent": Output("sent", bool, "Message sent status")}
        super().__init__("message_sender", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        message: LLMChatResponse = kwargs["message"]
        # Here you would implement the actual message sending logic
        # This is a placeholder implementation
        try:
            # Simulate sending message
            adapter: IMAdapter = self.container.resolve(IMAdapter)
            # adapter.send_message(message.choices[0].message.content)
            print(f"Sending message: {message}")
            return {"sent": True}
        except Exception as e:
            print(f"Failed to send message: {str(e)}")
            return {"sent": False}

class DefaultWorkflow(Workflow):
    def __init__(self, container: DependencyContainer):
        # Create block instances
        message_converter = MessageConverterBlock(container)
        llm_chat = LLMChatBlock(container)
        message_sender = MessageSenderBlock(container)
        # Create input block for IMMessage
        im_message_input = IMMessageInputBlock(container)

        # Create wires to connect the blocks
        input_to_converter = Wire(im_message_input, "message", message_converter, "message")
        converter_to_llm = Wire(message_converter, "llm_message", llm_chat, "prompt")
        llm_to_sender = Wire(llm_chat, "response", message_sender, "message")

        # Initialize workflow with blocks and wires
        super().__init__(
            [im_message_input, message_converter, llm_chat, message_sender],
            [input_to_converter, converter_to_llm, llm_to_sender]
        )
        
        self.container = container