from typing import Any, Dict, List

from pydantic import BaseModel, Field


class IMConfig(BaseModel):
    """IM配置"""
    name: str = Field(default="", description="IM标识名称")
    enable: bool = Field(default=True, description="是否启用IM")
    adapter: str = Field(default="dummy", description="IM适配器类型")
    config: Dict[str, Any] = Field(default={}, description="IM的配置")

class LLMBackendConfig(BaseModel):
    """LLM后端配置"""
    name: str = Field(description="后端标识名称")
    adapter: str = Field(description="LLM适配器类型")
    config: Dict[str, Any] = Field(default={}, description="后端配置")
    enable: bool = Field(default=True, description="是否启用")
    models: List[str] = Field(default=[], description="支持的模型列表")

class LLMConfig(BaseModel):
    api_backends: List[LLMBackendConfig] = Field(default=[], description="LLM API后端列表")

class DefaultConfig(BaseModel):
    llm_model: str = Field(default="gemini-1.5-flash", description="默认使用的 LLM 模型名称")

class MemoryPersistenceConfig(BaseModel):
    type: str = Field(default="file", description="持久化类型: file/redis")
    file: Dict[str, Any] = Field(
        default={
            "storage_dir": "./data/memory"
        },
        description="文件持久化配置"
    )
    redis: Dict[str, Any] = Field(
        default={
            "host": "localhost",
            "port": 6379,
            "db": 0
        },
        description="Redis持久化配置"
    )

class MemoryConfig(BaseModel):
    persistence: MemoryPersistenceConfig = MemoryPersistenceConfig()
    max_entries: int = Field(default=100, description="每个作用域最大记忆条目数")
    default_scope: str = Field(default="member", description="默认作用域类型")
    
class WebConfig(BaseModel):
    host: str = Field(default="127.0.0.1", description="Web服务绑定的IP地址")
    port: int = Field(default=8080, description="Web服务端口号")
    secret_key: str = Field(default="", description="Web服务的密钥，用于JWT等加密")
    password_file: str = Field(default="./data/web/password.hash", description="密码哈希存储路径")

class PluginConfig(BaseModel):
    """插件配置"""
    enable: List[str] = Field(default=[], description="启用的外部插件列表")
    market_base_url: str = Field(default="https://kirara-plugin.app.lss233.com/api/v1", description="插件市场基础URL")

class GlobalConfig(BaseModel):
    ims: List[IMConfig] = Field(default=[], description="IM配置列表")
    llms: LLMConfig = LLMConfig()
    defaults: DefaultConfig = DefaultConfig()
    memory: MemoryConfig = MemoryConfig()
    web: WebConfig = WebConfig()
    plugins: PluginConfig = PluginConfig()
