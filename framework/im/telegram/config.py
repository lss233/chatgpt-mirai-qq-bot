from pydantic import BaseModel, Field
from typing import List, Dict, Any

class TelegramConfig(BaseModel):
    """
    Telegram 配置文件模型。
    """
    token: str = Field(description="Telegram Bot Token")

    class Config:
        # 允许动态添加字段
        extra = "allow"

    def __repr__(self):
        return f"TelegramConfig(token={self.token})"