from typing import Optional

from pydantic import BaseModel

from kirara_ai.config.global_config import FrpcConfig


class FrpcStatus(BaseModel):
    """FRPC 状态"""
    is_running: bool
    is_installed: bool
    config: FrpcConfig
    version: str = ""
    remote_url: str = ""
    error_message: str = ""
    download_progress: float = 0


class FrpcConfigUpdate(BaseModel):
    """FRPC 配置更新请求"""
    enable: Optional[bool] = None
    server_addr: Optional[str] = None
    server_port: Optional[int] = None
    token: Optional[str] = None
    remote_port: Optional[int] = None


class FrpcDownloadProgress(BaseModel):
    """FRPC 下载进度"""
    progress: float
    status: str = "downloading"  # downloading, completed, error
    error_message: str = "" 