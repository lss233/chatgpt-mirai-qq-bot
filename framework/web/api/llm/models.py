from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from framework.config.global_config import LLMBackendConfig


class LLMBackendInfo(LLMBackendConfig):
    """LLM后端信息"""



class LLMBackendList(BaseModel):
    """LLM后端列表"""

    backends: List[LLMBackendInfo]


class LLMBackendResponse(BaseModel):
    """LLM后端响应"""

    error: Optional[str] = None
    data: Optional[LLMBackendInfo] = None


class LLMBackendListResponse(BaseModel):
    """LLM后端列表响应"""

    error: Optional[str] = None
    data: Optional[LLMBackendList] = None


class LLMBackendCreateRequest(LLMBackendConfig):
    """创建LLM后端请求"""



class LLMBackendUpdateRequest(LLMBackendConfig):
    """更新LLM后端请求"""



class LLMAdapterTypes(BaseModel):
    """可用的LLM适配器类型列表"""

    types: List[str]


class LLMAdapterConfigSchema(BaseModel):
    """LLM适配器配置模式"""

    error: Optional[str] = None
    configSchema: Optional[Dict[str, Any]] = None
