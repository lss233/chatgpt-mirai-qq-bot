from dataclasses import dataclass
from typing import Dict, Any
from framework.im.sender import ChatSender
from datetime import datetime

@dataclass
class MemoryEntry:
    """基础记忆条目"""

    sender: ChatSender
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]