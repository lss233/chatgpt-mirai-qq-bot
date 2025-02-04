import json
from datetime import datetime
from framework.im.sender import ChatSender, ChatType
class MemoryJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ChatSender):
            return {
                "__type__": "ChatSender",
                "user_id": obj.user_id,
                "chat_type": obj.chat_type.value,
                "group_id": obj.group_id,
                "raw_metadata": obj.raw_metadata
            }
        elif isinstance(obj, ChatType):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def memory_json_decoder(obj):
    if "__type__" in obj:
        if obj["__type__"] == "ChatSender":
            return ChatSender(
                user_id=obj["user_id"],
                chat_type=ChatType(obj["chat_type"]),
                group_id=obj["group_id"],
                raw_metadata=obj["raw_metadata"]
            )
    return obj

