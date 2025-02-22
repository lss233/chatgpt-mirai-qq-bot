from typing import Any, Dict, Optional

from kirara_ai.im.adapter import IMAdapter, UserProfileAdapter
from kirara_ai.im.profile import UserProfile
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.core.block import Block
from kirara_ai.workflow.core.block.input_output import Input, Output


class QueryUserProfileBlock(Block):
    def __init__(self, container: DependencyContainer):
        inputs = {
            "chat_sender": Input(
                "chat_sender", "聊天对象", ChatSender, "要查询聊天对象的 profile"
            ),
            "im_adapter": Input(
                "im_adapter", "IM 平台", IMAdapter, "IM 平台适配器", optional=True
            ),
        }
        outputs = {"profile": Output("profile", "用户资料", UserProfile, "用户资料")}
        super().__init__("query_user_profile", inputs, outputs)
        self.container = container

    def execute(
        self, chat_sender: ChatSender, im_adapter: Optional[IMAdapter] = None
    ) -> Dict[str, Any]:
        # 如果没有提供 im_adapter，则从容器中获取默认的
        if im_adapter is None:
            im_adapter = self.container.resolve(IMAdapter)

        # 检查 im_adapter 是否实现了 UserProfileAdapter 协议
        if not isinstance(im_adapter, UserProfileAdapter):
            raise TypeError(
                f"IM Adapter {type(im_adapter)} does not support user profile querying"
            )

        # 同步调用异步方法（在工作流执行器中会被正确处理）
        profile = im_adapter.query_user_profile(chat_sender)

        return {"profile": profile}
