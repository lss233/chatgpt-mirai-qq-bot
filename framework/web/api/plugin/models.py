from typing import Dict, Any, List, Optional
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
    metadata: Optional[Dict[str, Any]] = None

class PluginList(BaseModel):
    """插件列表响应"""
    plugins: List[PluginInfo]

class PluginResponse(BaseModel):
    """单个插件响应"""
    plugin: PluginInfo

class InstallPluginRequest(BaseModel):
    """安装插件请求"""
    package_name: str
    version: Optional[str] = None  # 可选的版本号，不指定则安装最新版 