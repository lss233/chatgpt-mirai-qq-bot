from typing import Dict, Any, List
from pydantic import BaseModel

class SystemStatus(BaseModel):
    """系统状态信息"""
    version: str = "1.0.0"
    uptime: float
    active_adapters: int
    active_backends: int
    loaded_plugins: int
    workflow_count: int
    memory_usage: Dict[str, Any]
    cpu_usage: float

class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    status: SystemStatus 