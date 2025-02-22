from enum import Enum, auto
from typing import Optional

from pydantic import BaseModel, Field


class Gender(Enum):
    MALE = auto()
    FEMALE = auto()
    UNKNOWN = auto()
    OTHER = auto()


class UserProfile(BaseModel):
    """
    通用的用户资料结构
    """

    user_id: str = Field(..., description="用户唯一标识")
    username: Optional[str] = Field(None, description="用户名")
    display_name: Optional[str] = Field(None, description="显示名称")
    full_name: Optional[str] = Field(None, description="完整名称")
    gender: Optional[Gender] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    level: Optional[int] = Field(None, description="用户等级")
    language: Optional[str] = Field(None, description="语言")
    extra_info: Optional[dict] = Field(None, description="平台特定的额外信息")
