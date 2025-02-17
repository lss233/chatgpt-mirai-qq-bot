from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from framework.im.sender import ChatSender


@dataclass
class MemoryEntry:
    """基础记忆条目"""

    sender: ChatSender
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
