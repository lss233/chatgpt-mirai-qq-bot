from typing import Dict, List, Optional

from pydantic import BaseModel, Field

class IMConfig(BaseModel):
    enable: Dict[str, List[str]] = dict()
    configs: Dict[str, Dict[str, str]] = Field(description="IM 的凭证配置", default=dict())

class LLMBackendConfig(BaseModel):
    enable: bool
    adapter: str
    configs: List[Dict]
    models: List[str]

class LLMConfig(BaseModel):
    backends: Dict[str, LLMBackendConfig] = dict()
    
class GlobalConfig(BaseModel):
    ims: IMConfig = IMConfig()
    llms: LLMConfig = LLMConfig()
