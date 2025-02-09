from typing import Dict, Any, Optional
from framework.ioc.container import DependencyContainer
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input
from framework.workflow.core.block.input_output import Output
from framework.im.sender import ChatSender
from framework.im.adapter import IMAdapter, UserProfileAdapter
from framework.im.profile import UserProfile

class QueryUserProfileBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {
            "chat_sender": Input("chat_sender", ChatSender, "Chat sender to query profile for"),
            "im_adapter": Input("im_adapter", IMAdapter, "IM Adapter to use for profile query", optional=True)
        }
        outputs = {
            "profile": Output("profile", UserProfile, "User profile information")
        }
        super().__init__("query_user_profile", inputs, outputs)
        self.container = container

    def execute(self, chat_sender: ChatSender, im_adapter: Optional[IMAdapter] = None) -> Dict[str, Any]:
        # 如果没有提供 im_adapter，则从容器中获取默认的
        if im_adapter is None:
            im_adapter = self.container.resolve(IMAdapter)
        
        # 检查 im_adapter 是否实现了 UserProfileAdapter 协议
        if not isinstance(im_adapter, UserProfileAdapter):
            raise TypeError(f"IM Adapter {type(im_adapter)} does not support user profile querying")
        
        # 同步调用异步方法（在工作流执行器中会被正确处理）
        profile = im_adapter.query_user_profile(chat_sender)
        
        return {"profile": profile} 