
import pytest
import pytest_asyncio

from framework.ioc.container import DependencyContainer
from framework.web.app import create_app
from tests.utils.auth_test_utils import TEST_PASSWORD, setup_auth_service

# ==================== 常量区 ====================
TEST_NEW_PASSWORD = "new-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_TOKEN = "mock_token"  # 使用 MockAuthService 的固定 token


# ==================== Fixtures ====================
@pytest.fixture
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    setup_auth_service(container)
    return create_app(container)


@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest_asyncio.fixture
async def auth_token(test_client):
    """获取认证token"""
    response = await test_client.post(
        "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
    )
    data = await response.get_json()
    assert "access_token" in data
    return data["access_token"]


# ==================== 测试用例 ====================
class TestAuth:
    @pytest.mark.asyncio
    async def test_check_first_time(self, test_client):
        """测试检查是否首次访问接口"""
        # 首次访问
        response = await test_client.get("/backend-api/api/auth/check-first-time")
        assert response.status_code == 200
        data = await response.get_json()
        assert "is_first_time" in data
        assert data["is_first_time"] == True

        # 模拟登录后
        await test_client.post(
            "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
        )

        # 再次检查
        response = await test_client.get("/backend-api/api/auth/check-first-time")
        assert response.status_code == 200
        data = await response.get_json()
        assert "is_first_time" in data
        assert data["is_first_time"] == False

    @pytest.mark.asyncio
    async def test_normal_login(self, test_client):
        """测试普通登录"""
        # 先进行首次登录设置密码
        await test_client.post(
            "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
        )

        # 然后测试正常登录
        response = await test_client.post(
            "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
        )

        assert response.status_code == 200
        data = await response.get_json()
        assert "access_token" in data
        assert data["access_token"] == TEST_TOKEN

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client):
        """测试密码错误的情况"""
        # 先进行首次登录设置密码
        await test_client.post(
            "/backend-api/api/auth/login", json={"password": TEST_PASSWORD}
        )

        # 然后测试错误密码
        response = await test_client.post(
            "/backend-api/api/auth/login", json={"password": "wrong-password"}
        )

        assert response.status_code == 401
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_change_password(self, test_client, auth_token):
        """测试修改密码"""
        response = await test_client.post(
            "/backend-api/api/auth/change-password",
            json={"old_password": TEST_PASSWORD, "new_password": TEST_NEW_PASSWORD},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200

        # 验证新密码可以登录
        response = await test_client.post(
            "/backend-api/api/auth/login", json={"password": TEST_NEW_PASSWORD}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, test_client, auth_token):
        """测试修改密码时旧密码错误的情况"""
        response = await test_client.post(
            "/backend-api/api/auth/change-password",
            json={"old_password": "wrong-password", "new_password": TEST_NEW_PASSWORD},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 401
        data = await response.get_json()
        assert "error" in data
