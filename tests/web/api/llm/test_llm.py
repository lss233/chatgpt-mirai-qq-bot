import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open

import pytest_asyncio
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig, LLMBackendConfig
from framework.llm.llm_registry import LLMBackendRegistry, LLMAbility
from framework.llm.llm_manager import LLMManager
from framework.llm.adapter import LLMBackendAdapter
from framework.llm.format.request import LLMChatRequest
from framework.llm.format.response import LLMChatResponse
from framework.config.config_loader import ConfigLoader
from pydantic import BaseModel

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_BACKEND_NAME = "test-backend"
TEST_ADAPTER_TYPE = "test-adapter"

# ==================== 测试用适配器 ====================
class TestConfig(BaseModel):
    """测试用配置"""
    __test__ = False
    api_key: str = "test-key"
    model: str = "test-model"

class TestAdapter(LLMBackendAdapter):
    """测试用LLM适配器"""
    __test__ = False
    def __init__(self, config: TestConfig):
        self.config = config

        
    def chat(self, req: LLMChatRequest) -> LLMChatResponse:
        return LLMChatResponse(
            content="Test response",
            model=self.config.model,
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        )

# ==================== Fixtures ====================
@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    
    # 配置mock
    config = GlobalConfig()
    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY,
        password_file="test_password.hash"
    )
    config.llms.api_backends = [
        LLMBackendConfig(
            name=TEST_BACKEND_NAME,
            adapter=TEST_ADAPTER_TYPE,
            config={
                'api_key': 'test-key',
                'model': 'test-model'
            },
            enable=True,
            models=['test-model']
        )
    ]
    container.register(GlobalConfig, config)
    
    # 注册LLM组件
    registry = LLMBackendRegistry()
    registry.register(TEST_ADAPTER_TYPE, TestAdapter, TestConfig, LLMAbility.TextChat)
    container.register(LLMBackendRegistry, registry)
    
    manager = LLMManager(container)
    container.register(LLMManager, manager)
    
    app = create_app(container)
    app.container = container
    return app

@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest_asyncio.fixture
async def auth_headers(test_client):
    """获取认证头"""
    with patch('framework.web.auth.routes.verify_saved_password', return_value=True):
        response = await test_client.post('/api/auth/login', json={
            'password': TEST_PASSWORD
        })
        data = await response.get_json()
        assert "error" not in data
        token = data['access_token']
        return {'Authorization': f'Bearer {token}'}

# ==================== 测试用例 ====================
class TestLLMBackend:
    @pytest.mark.asyncio
    async def test_get_adapter_types(self, test_client, auth_headers):
        """测试获取适配器类型列表"""
        response = await test_client.get('/api/llm/types', headers=auth_headers)
        
        data = await response.get_json()
        assert 'types' in data
        assert TEST_ADAPTER_TYPE in data.get('types')
        
    @pytest.mark.asyncio
    async def test_list_backends(self, test_client, auth_headers):
        """测试获取后端列表"""
        response = await test_client.get('/api/llm/backends', headers=auth_headers)
        
        data = await response.get_json()
        assert 'data' in data
        assert 'backends' in data.get('data')
        backends = data.get('data').get('backends')
        assert len(backends) == 1
        assert backends[0].get('name') == TEST_BACKEND_NAME
        assert backends[0].get('adapter') == TEST_ADAPTER_TYPE
        
    @pytest.mark.asyncio
    async def test_get_backend(self, test_client, auth_headers):
        """测试获取指定后端"""
        response = await test_client.get(
            f'/api/llm/backends/{TEST_BACKEND_NAME}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert 'data' in data
        backend = data.get('data')
        assert backend.get('name') == TEST_BACKEND_NAME
        assert backend.get('adapter') == TEST_ADAPTER_TYPE
        
    @pytest.mark.asyncio
    async def test_create_backend(self, test_client, auth_headers):
        """测试创建新后端"""
        new_backend = LLMBackendConfig(
            name='new-backend',
            adapter=TEST_ADAPTER_TYPE,
            config={
                'api_key': 'new-key',
                'model': 'new-model'
            },
            enable=True,
            models=['new-model']
        )
        
        # Mock 配置文件保存
        with patch("framework.config.config_loader.ConfigLoader.save_config_with_backup") as mock_save:
            response = await test_client.post(
                '/api/llm/backends',
                headers=auth_headers,
                json=new_backend.model_dump()
            )
            
            data = await response.get_json()
            assert 'data' in data
            backend = data.get('data')
            assert backend.get('name') == 'new-backend'
            assert backend.get('adapter') == TEST_ADAPTER_TYPE
            
            # 验证配置保存
            mock_save.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_update_backend(self, test_client, auth_headers):
        """测试更新后端"""
        updated_config = LLMBackendConfig(
            name=TEST_BACKEND_NAME,
            adapter=TEST_ADAPTER_TYPE,
            config={
                'api_key': 'updated-key',
                'model': 'updated-model'
            },
            enable=True,
            models=['updated-model']
        )
        
        # Mock 配置文件保存
        ConfigLoader.save_config_with_backup = MagicMock()
        response = await test_client.put(
            f'/api/llm/backends/{TEST_BACKEND_NAME}',
            headers=auth_headers,
            json=updated_config.model_dump()
        )
        
        data = await response.get_json()
        assert 'data' in data
        backend = data.get('data')
        assert backend.get('name') == TEST_BACKEND_NAME
        assert backend.get('config').get('api_key') == 'updated-key'
    
        # 验证配置保存
        ConfigLoader.save_config_with_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_backend(self, test_client, auth_headers):
        """测试删除后端"""
        ConfigLoader.save_config_with_backup = MagicMock()
        response = await test_client.delete(
            f'/api/llm/backends/{TEST_BACKEND_NAME}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert 'data' in data
        backend = data.get('data')
        assert backend.get('name') == TEST_BACKEND_NAME
        ConfigLoader.save_config_with_backup.assert_called_once()
        
        # 验证后端已被删除
        response = await test_client.get(
            f'/api/llm/backends/{TEST_BACKEND_NAME}',
            headers=auth_headers
        )
        data = await response.get_json()
        assert 'error' in data