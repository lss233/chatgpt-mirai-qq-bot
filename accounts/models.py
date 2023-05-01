from pydantic import BaseModel


class AccountInfoBaseModel(BaseModel):
    ok: bool = False
    """是否可用"""

    async def check_alive(self) -> bool: ...
    """
    检查账号可用性
    通过一个幂等的 API 请求来确保此账号信息仍然可用
    """
