import pytest
from unittest.mock import patch, MagicMock

import pytest_asyncio
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_NEW_PASSWORD = "new-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_TOKEN = "test-token"

# ==================== Fixtures ====================
@pytest.fixture
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    
    # 配置mock
    config = GlobalConfig()
    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY,
        password_file="test_password.hash"
    )
    container.register(GlobalConfig, config)
    
    app = create_app(container)
    return app

@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest_asyncio.fixture
async def auth_token(test_client):
    """获取认证token"""
    with patch('framework.web.auth.routes.verify_saved_password', return_value=True):
        response = await test_client.post('/api/auth/login', json={
            'password': TEST_PASSWORD
        })
        data = await response.get_json()
        assert 'access_token' in data
        return data['access_token']

# ==================== 测试用例 ====================
class TestAuth:
    @pytest.mark.asyncio
    async def test_first_time_login(self, test_client):
        """测试首次登录"""
        # Mock is_first_time返回True
        with patch('framework.web.auth.routes.is_first_time', return_value=True), \
             patch('framework.web.auth.routes.save_password') as mock_save, \
             patch('framework.web.auth.routes.create_access_token', return_value=TEST_TOKEN):
            
            response = await test_client.post('/api/auth/login', json={
                'password': TEST_PASSWORD
            })
            
            assert response.status_code == 200
            data = await response.get_json()
            assert 'access_token' in data
            assert data['access_token'] == TEST_TOKEN
            mock_save.assert_called_once_with(TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_normal_login(self, test_client):
        """测试普通登录"""
        # Mock is_first_time返回False
        with patch('framework.web.auth.routes.is_first_time', return_value=False), \
             patch('framework.web.auth.routes.verify_saved_password', return_value=True), \
             patch('framework.web.auth.routes.create_access_token', return_value=TEST_TOKEN):
            
            response = await test_client.post('/api/auth/login', json={
                'password': TEST_PASSWORD
            })
            
            assert response.status_code == 200
            data = await response.get_json()
            assert 'access_token' in data
            assert data['access_token'] == TEST_TOKEN

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client):
        """测试密码错误的情况"""
        with patch('framework.web.auth.routes.is_first_time', return_value=False), \
             patch('framework.web.auth.routes.verify_saved_password', return_value=False):
            
            response = await test_client.post('/api/auth/login', json={
                'password': TEST_PASSWORD
            })
            
            assert response.status_code == 401
            data = await response.get_json()
            assert 'error' in data

    @pytest.mark.asyncio
    async def test_change_password(self, test_client, auth_token):
        """测试修改密码"""
        with patch('framework.web.auth.routes.verify_saved_password', return_value=True), \
             patch('framework.web.auth.routes.save_password') as mock_save:
            
            response = await test_client.post(
                '/api/auth/change-password',
                json={
                    'old_password': TEST_PASSWORD,
                    'new_password': TEST_NEW_PASSWORD
                },
                headers={'Authorization': f'Bearer {auth_token}'}
            )
            
            assert response.status_code == 200
            mock_save.assert_called_once_with(TEST_NEW_PASSWORD)

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, test_client, auth_token):
        """测试修改密码时旧密码错误的情况"""
        with patch('framework.web.auth.routes.verify_saved_password', return_value=False):
            response = await test_client.post(
                '/api/auth/change-password',
                json={
                    'old_password': 'wrong-password',
                    'new_password': TEST_NEW_PASSWORD
                },
                headers={'Authorization': f'Bearer {auth_token}'}
            )
            
            assert response.status_code == 401
            data = await response.get_json()
            assert 'error' in data 