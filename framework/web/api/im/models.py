from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from framework.config.global_config import IMConfig

IMAdapterConfig = IMConfig

class IMAdapterStatus(IMAdapterConfig):
    """IM适配器状态"""
    is_running: bool

class IMAdapterList(BaseModel):
    """IM适配器列表响应"""
    adapters: List[IMAdapterStatus]

class IMAdapterResponse(BaseModel):
    """单个IM适配器响应"""
    adapter: IMAdapterStatus

class IMAdapterTypes(BaseModel):
    """可用的IM适配器类型列表"""
    types: List[str]

class IMAdapterConfigSchema(BaseModel):
    """IM适配器配置模式"""
    error: Optional[str] = None
    configSchema: Optional[Dict[str, Any]] = None 