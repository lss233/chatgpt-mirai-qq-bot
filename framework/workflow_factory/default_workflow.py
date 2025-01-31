import asyncio
from typing import Any, Dict, List
from framework.im.adapter import IMAdapter
from framework.llm.format.message import LLMChatMessage
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.llm.llm_manager import LLMManager
from framework.workflow_executor.workflow import Wire, Workflow
from framework.im.message import IMMessage, TextMessage
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
    
class ResponseConverterBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"response": Input("response", LLMChatResponse, "Input LLM response")}
        outputs = {"im_message": Output("im_message", IMMessage, "Converted IM message")}
        super().__init__("response_converter", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        llm_response: LLMChatResponse = kwargs["response"]
        
        # Extract the content from LLMChatResponse
        content = ""
        if llm_response.choices and len(llm_response.choices) > 0:
            if llm_response.choices[0].message:
                content = llm_response.choices[0].message.content
        
        # Create TextMessage element
        text_element = TextMessage(content)
        
        # Create IMMessage with system as sender
        im_message = IMMessage(
            sender="<@llm>",
            message_elements=[text_element]
        )
        
        return {"im_message": im_message}


class IMSendBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {"im_message": Input("im_message", IMMessage, "Response to send")}
        outputs = {"sent": Output("sent", bool, "Message sent status")}
        super().__init__("message_sender", inputs, outputs)
        self.container = container

    def execute(self, **kwargs) -> Dict[str, Any]:
        message: LLMChatResponse = kwargs["im_message"]
        source_message: IMMessage = self.container.resolve(IMMessage)
        source = source_message.sender
        try:
            # Simulate sending message
            adapter: IMAdapter = self.container.resolve(IMAdapter)
            asyncio.run(adapter.send_message(message, source))
            
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
        response_converter = ResponseConverterBlock(container)  # Add new block
        message_sender = IMSendBlock(container)
        im_message_input = IMMessageInputBlock(container)

        # Create wires to connect the blocks
        input_to_converter = Wire(im_message_input, "message", message_converter, "message")
        converter_to_llm = Wire(message_converter, "llm_message", llm_chat, "prompt")
        llm_to_response_converter = Wire(llm_chat, "response", response_converter, "response")  # Add new wire
        response_converter_to_sender = Wire(response_converter, "im_message", message_sender, "im_message")  # Update wire

        # Initialize workflow with blocks and wires
        super().__init__(
            [im_message_input, message_converter, llm_chat, response_converter, message_sender],  # Add new block
            [input_to_converter, converter_to_llm, llm_to_response_converter, response_converter_to_sender]  # Update wires
        )
        
        self.container = container