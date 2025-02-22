from kirara_ai.im.sender import ChatSender, ChatType

from .base import MemoryScope


# 默认实现
class MemberScope(MemoryScope):
    """群成员作用域"""

    def get_scope_key(self, sender: ChatSender) -> str:
        if sender.chat_type == ChatType.GROUP:
            return f"member:{sender.group_id}:{sender.user_id}"
        else:
            return f"c2c:{sender.user_id}"

    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        if target_sender.chat_type != query_sender.chat_type:
            return False

        if target_sender.chat_type == ChatType.GROUP:
            return (
                target_sender.group_id == query_sender.group_id
                and target_sender.user_id == query_sender.user_id
            )
        else:
            return target_sender.user_id == query_sender.user_id


class GroupScope(MemoryScope):
    """群作用域"""

    def get_scope_key(self, sender: ChatSender) -> str:
        if sender.chat_type == ChatType.GROUP:
            return f"group:{sender.group_id}"
        else:
            return f"c2c:{sender.user_id}"

    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        if target_sender.chat_type != query_sender.chat_type:
            return False

        if target_sender.chat_type == ChatType.GROUP:
            return target_sender.group_id == query_sender.group_id
        else:
            return target_sender.user_id == query_sender.user_id


class GlobalScope(MemoryScope):
    """全局作用域"""

    def get_scope_key(self, sender: ChatSender) -> str:
        return "global"

    def is_in_scope(self, target_sender: ChatSender, query_sender: ChatSender) -> bool:
        return True
