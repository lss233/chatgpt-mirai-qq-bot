from typing import Dict, List

from pydantic import BaseModel, Field

class IMConfig(BaseModel):
    enable: Dict[str, List[str]]
    configs: Dict[str, Dict[str, str]] = Field(description="IM 的凭证配置")

class LLMBackendConfig(BaseModel):
    enable: bool
    adapter: str
    configs: List[Dict]
    models: List[str]

class LLMConfig(BaseModel):
    backends: Dict[str, LLMBackendConfig]
    
class GlobalConfig(BaseModel):
    ims: IMConfig
    llms: LLMConfig
