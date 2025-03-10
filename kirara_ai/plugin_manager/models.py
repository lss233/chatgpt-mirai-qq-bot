from typing import Any, Dict, Optional

from pydantic import BaseModel


class PluginInfo(BaseModel):
    """插件信息"""

    name: str
    package_name: Optional[str] = None  # 外部插件的包名
    description: str
    version: str
    author: str
    is_internal: bool  # 是否为内部插件
    is_enabled: bool  # 是否启用
    requires_restart: bool = False # 是否需要重启
    metadata: Optional[Dict[str, Any]] = None
