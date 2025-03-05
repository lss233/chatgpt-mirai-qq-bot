import json
from datetime import datetime
from types import FunctionType

from kirara_ai.im.sender import ChatSender, ChatType


class MemoryJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ChatSender):
            return {
                "__type__": "ChatSender",
                "user_id": obj.user_id,
                "chat_type": obj.chat_type.value,
                "group_id": obj.group_id,
                "display_name": obj.display_name,
                "raw_metadata": obj.raw_metadata,
            }
        elif isinstance(obj, ChatType):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, FunctionType):
            return {
                "__type__": "function",
                "name": obj.__name__,
                "args": obj.__code__.co_varnames[:obj.__code__.co_argcount],
                "defaults": obj.__defaults__,
                "kwdefaults": obj.__kwdefaults__,
                "doc": obj.__doc__,
            }
        return super().default(obj)


def memory_json_decoder(obj):
    if "__type__" in obj:
        if obj["__type__"] == "ChatSender":
            return ChatSender(
                user_id=obj["user_id"],
                chat_type=ChatType(obj["chat_type"]),
                group_id=obj["group_id"],
                display_name=obj["display_name"],
                raw_metadata=obj["raw_metadata"],
            )
    return obj
