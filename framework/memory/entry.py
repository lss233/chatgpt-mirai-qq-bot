from dataclasses import dataclass, field
from typing import Dict, Any
from framework.im.sender import ChatSender
from datetime import datetime

@dataclass
class MemoryEntry:
    """基础记忆条目"""

    sender: ChatSender
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)