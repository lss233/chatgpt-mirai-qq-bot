from typing import List, Optional

from pydantic import BaseModel

from framework.plugin_manager.models import PluginInfo


class PluginList(BaseModel):
    """插件列表响应"""

    plugins: List[PluginInfo]


class PluginResponse(BaseModel):
    """插件详情响应"""

    plugin: PluginInfo


class InstallPluginRequest(BaseModel):
    """安装插件请求"""

    package_name: str
    version: Optional[str] = None  # 可选的版本号，不指定则安装最新版
