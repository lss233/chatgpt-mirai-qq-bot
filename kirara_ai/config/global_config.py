from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kirara_ai.llm.model_types import LLMAbility, ModelType


class IMConfig(BaseModel):
    """IM配置"""

    name: str = Field(default="", description="IM标识名称")
    enable: bool = Field(default=True, description="是否启用IM")
    adapter: str = Field(default="dummy", description="IM适配器类型")
    config: Dict[str, Any] = Field(default={}, description="IM的配置")


class ModelConfig(BaseModel):
    """模型配置"""
    
    id: str = Field(description="模型标识ID")
    type: str = Field(default=ModelType.LLM.value, description="模型类型：llm/embedding/image_generation等")
    ability: int = Field(description="模型能力，对应模型类型的Ability枚举值")

    model_config = ConfigDict(extra="allow")

class LLMBackendConfig(BaseModel):
    """LLM后端配置"""

    name: str = Field(description="后端标识名称")
    adapter: str = Field(description="LLM适配器类型")
    config: Dict[str, Any] = Field(default={}, description="后端配置")
    enable: bool = Field(default=True, description="是否启用")
    models: List[ModelConfig] = Field(
        default=[], description="支持的模型列表"
    )
    
    @model_validator(mode='before')
    @classmethod
    def migrate_models_format(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动迁移模型配置格式
        将旧格式的字符串ID列表转换为新格式的ModelConfig对象列表
        """
        if "models" in data and isinstance(data["models"], list):
            # 创建新的模型列表
            new_models = []
            
            for model in data["models"]:
                if isinstance(model, str):
                    # 旧格式：字符串ID，转换为ModelConfig
                    new_models.append(ModelConfig(id=model, type=ModelType.LLM.value, ability=LLMAbility.TextChat.value))
                else:
                    # 新格式或已迁移的模型配置，保持不变
                    new_models.append(model)
            
            data["models"] = new_models
            
        return data


class LLMConfig(BaseModel):
    api_backends: List[LLMBackendConfig] = Field(
        default=[], description="LLM API后端列表"
    )

class MCPServerConfig(BaseModel):
    """MCP服务器配置"""
    
    id: str = Field(description="服务器标识ID")
    description: str = Field(default="", description="服务器描述")
    url: Optional[str] = Field(default="", description="服务器URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="服务器请求 Headers")
    command: Optional[str] = Field(default="", description="服务器命令")
    args: List[str] = Field(default_factory=list, description="服务器参数")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    connection_type: str = Field(default="stdio", description="连接类型: stdio/sse")
    enable: bool = Field(default=True, description="是否启用")
    

class MCPConfig(BaseModel):
    """MCP配置"""
    servers: List[MCPServerConfig] = Field(default=[], description="MCP服务器列表")


class DefaultConfig(BaseModel):
    llm_model: str = Field(
        default="gemini-1.5-flash", description="默认使用的 LLM 模型名称"
    )


class MemoryPersistenceConfig(BaseModel):
    type: str = Field(default="file", description="持久化类型: file/redis")
    file: Dict[str, Any] = Field(
        default={"storage_dir": "./data/memory"}, description="文件持久化配置"
    )
    redis: Dict[str, Any] = Field(
        default={"host": "localhost", "port": 6379, "db": 0},
        description="Redis持久化配置",
    )


class MemoryConfig(BaseModel):
    persistence: MemoryPersistenceConfig = MemoryPersistenceConfig()
    max_entries: int = Field(default=100, description="每个作用域最大记忆条目数")
    default_scope: str = Field(default="member", description="默认作用域类型")


class WebConfig(BaseModel):
    host: str = Field(default="127.0.0.1", description="Web服务绑定的IP地址")
    port: int = Field(default=8080, description="Web服务端口号")
    secret_key: str = Field(default="", description="Web服务的密钥，用于JWT等加密")
    password_file: str = Field(
        default="./data/web/password.hash", description="密码哈希存储路径"
    )


class PluginConfig(BaseModel):
    """插件配置"""

    enable: List[str] = Field(default=[], description="启用的外部插件列表")
    market_base_url: str = Field(
        default="https://kirara-plugin.app.lss233.com/api/v1",
        description="插件市场基础URL",
    )


class UpdateConfig(BaseModel):
    pypi_registry: str = Field(default="https://pypi.org/simple", description="PyPI 服务器 URL")
    npm_registry: str = Field(default="https://registry.npmjs.org", description="npm 服务器 URL")


class FrpcConfig(BaseModel):
    """FRPC 配置"""
    
    enable: bool = Field(default=False, description="是否启用 FRPC")
    server_addr: str = Field(default="", description="FRPC 服务器地址")
    server_port: int = Field(default=7000, description="FRPC 服务器端口")
    token: str = Field(default="", description="FRPC 连接令牌")
    remote_port: int = Field(default=0, description="远程端口，0 表示随机分配")


class SystemConfig(BaseModel):
    """系统配置"""

    timezone: str = Field(default="Asia/Shanghai", description="时区")


class TracingConfig(BaseModel):
    """Tracing 配置"""
    
    llm_tracing_content: bool = Field(default=False, description="是否记录 LLM 请求内容")

class MediaConfig(BaseModel):
    """媒体配置"""
    cleanup_duration: int = Field(default=30, description="间隔多少天清理一次媒体文件")
    auto_remove_unreferenced: bool = Field(default=True, description="是否自动删除未引用的媒体文件")
    last_cleanup_time: int = Field(default=0, description="上次清理时间")

class GlobalConfig(BaseModel):
    ims: List[IMConfig] = Field(default=[], description="IM配置列表")
    llms: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    defaults: DefaultConfig = DefaultConfig()
    memory: MemoryConfig = MemoryConfig()
    web: WebConfig = WebConfig()
    plugins: PluginConfig = PluginConfig()
    update: UpdateConfig = UpdateConfig()
    frpc: FrpcConfig = FrpcConfig()
    system: SystemConfig = SystemConfig()
    tracing: TracingConfig = TracingConfig()
    media: MediaConfig = MediaConfig()

    model_config = ConfigDict(extra="allow")
