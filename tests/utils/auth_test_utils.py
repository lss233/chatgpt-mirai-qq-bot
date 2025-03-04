import pytest_asyncio

from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.web.auth.services import AuthService, MockAuthService

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"


# ==================== Auth Fixtures ====================
def setup_auth_service(container: DependencyContainer) -> None:
    """设置认证服务"""

    # 注册 MockAuthService
    container.register(AuthService, MockAuthService())


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_client):
    """获取认证头"""

    response = test_client.post(
        "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
    )
    data = response.json()
    assert "error" not in data
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
