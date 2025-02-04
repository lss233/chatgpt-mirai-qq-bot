from typing import Dict, Any, List
from pydantic import BaseModel

class IMAdapterConfig(BaseModel):
    """IM适配器配置"""
    adapter_id: str
    adapter_type: str
    configs: Dict[str, Any]

class IMAdapterStatus(BaseModel):
    """IM适配器状态"""
    adapter_id: str
    adapter_type: str
    is_running: bool
    configs: Dict[str, Any]

class IMAdapterList(BaseModel):
    """IM适配器列表响应"""
    adapters: List[IMAdapterStatus]

class IMAdapterResponse(BaseModel):
    """单个IM适配器响应"""
    adapter: IMAdapterStatus

class IMAdapterTypes(BaseModel):
    """可用的IM适配器类型列表"""
    types: List[str] 