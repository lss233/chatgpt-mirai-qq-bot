from typing import Dict, Any, List
from pydantic import BaseModel

class LLMBackendConfig(BaseModel):
    """LLM后端配置"""
    backend_id: str
    adapter: str
    enable: bool
    configs: List[Dict[str, Any]]
    models: List[str]

class LLMBackendStatus(BaseModel):
    """LLM后端状态"""
    backend_id: str
    adapter: str
    enable: bool
    configs: List[Dict[str, Any]]
    models: List[str]
    is_available: bool

class LLMBackendList(BaseModel):
    """LLM后端列表响应"""
    backends: List[LLMBackendStatus]

class LLMBackendResponse(BaseModel):
    """单个LLM后端响应"""
    backend: LLMBackendStatus

class LLMAdapterTypes(BaseModel):
    """可用的LLM适配器类型列表"""
    types: List[str] 