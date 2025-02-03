from framework.ioc.container import DependencyContainer
from framework.workflow.core.workflow.builder import WorkflowBuilder
from framework.workflow.core.workflow import Workflow
from framework.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage
from framework.workflow.implementations.blocks.im.states import ToggleEditState
from framework.workflow.implementations.blocks.memory.chat_memory import ChatMemoryQuery, ChatMemoryStore
from framework.workflow.implementations.blocks.llm.chat import ChatMessageConstructor, ChatCompletion, ChatResponseConverter

def create_default_workflow(container: DependencyContainer) -> Workflow:
    """使用 DSL 创建默认工作流"""    
    system_prompt = """你是一个智能助手。以下是之前的对话历史：
{memory_content}

请基于以上历史记忆，回答用户的问题。"""

    user_prompt = """{user_msg}"""
    
    return (WorkflowBuilder("default_workflow", container)
        .use(GetIMMessage, name="get_message")
        .parallel([
            (ToggleEditState, {"is_editing": True}),
            (ChatMemoryQuery, "query_memory", {"memory_adapter": 'default_memory_adapter'})
        ])
        .chain(ChatMessageConstructor,
               wire_from=["query_memory", "get_message"],
               system_prompt_format=system_prompt,
               user_prompt_format=user_prompt)
        .chain(ChatCompletion, name="llm_chat")
        .chain(ChatResponseConverter)
        .parallel([
            SendIMMessage,
            (ChatMemoryStore, {"memory_adapter": 'default_memory_adapter'}, ["get_message", "llm_chat"]),
            (ToggleEditState, {"is_editing": False})
        ])
        .build())