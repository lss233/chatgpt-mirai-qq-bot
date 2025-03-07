from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from kirara_ai.config.global_config import IMConfig
from kirara_ai.im.im_registry import IMAdapterInfo
from kirara_ai.im.profile import UserProfile

IMAdapterConfig = IMConfig


class IMAdapterStatus(IMAdapterConfig):
    """IM适配器状态"""

    is_running: bool
    bot_profile: Optional[UserProfile] = None

class IMAdapterList(BaseModel):
    """IM适配器列表响应"""

    adapters: List[IMAdapterStatus]


class IMAdapterResponse(BaseModel):
    """单个IM适配器响应"""

    adapter: IMAdapterStatus


class IMAdapterTypes(BaseModel):
    """可用的IM适配器类型列表"""

    types: List[str]
    adapters: Dict[str, IMAdapterInfo]

class IMAdapterConfigSchema(BaseModel):
    """IM适配器配置模式"""

    error: Optional[str] = None
    configSchema: Optional[Dict[str, Any]] = None
