from typing import Dict, Optional

from pydantic import BaseModel


class SystemStatus(BaseModel):
    """系统状态信息"""

    version: str
    uptime: float
    active_adapters: int
    active_backends: int
    loaded_plugins: int
    workflow_count: int
    memory_usage: Dict[str, float]
    cpu_usage: float


class SystemStatusResponse(BaseModel):
    """系统状态响应"""

    status: SystemStatus


class UpdateStatus(BaseModel):
    status: str
    message: str


class UpdateCheckResponse(BaseModel):
    """更新检查响应"""
    current_backend_version: str
    latest_backend_version: str
    backend_update_available: bool
    backend_download_url: Optional[str]
    latest_webui_version: str
    webui_download_url: Optional[str]
