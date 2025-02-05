import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Any

import pytest_asyncio
from framework.web.api.im.models import IMAdapterConfig
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig, IMConfig
from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage, TextMessage
from framework.im.sender import ChatSender
from framework.config.config_loader import ConfigLoader
from unittest.mock import patch, MagicMock, mock_open
from pydantic import BaseModel, Field

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_ADAPTER_ID = "dummy-bot-1234"
TEST_ADAPTER_NOT_RUNNING_ID = "dummy-bot-2234"
TEST_ADAPTER_TYPE = "dummy"
TEST_ADAPTER_CONFIG = {
    "token": "test-token",
    "name": "Test Bot"
}

# ==================== 测试用 Adapter ====================
class DummyConfig(BaseModel):
    """Dummy 配置文件模型"""
    token: str = Field(description="Dummy Bot Token")
    name: str = Field(description="Bot Name")

class DummyAdapter(IMAdapter):
    """
    用于测试的 Dummy Adapter，实现基本的消息收发功能
    """
    def __init__(self, config: DummyConfig):
        self.config = config
        self.is_running = False
        self.messages = []  # 存储发送的消息
        self.editing_states = {}  # 存储编辑状态

    def convert_to_message(self, raw_message: Any) -> IMMessage:
        return IMMessage(
            sender=ChatSender.from_c2c_chat(
                user_id=raw_message.get("user_id", "default_user"),
                display_name=raw_message.get("display_name", "Default User")
            ),
            message_elements=[TextMessage(text=raw_message.get("text", ""))],
        )

    async def send_message(self, message: IMMessage, recipient: ChatSender):
        """发送消息"""
        self.messages.append((message, recipient))

    async def start(self):
        """启动 adapter"""
        self.is_running = True

    async def stop(self):
        """停止 adapter"""
        self.is_running = False

# ==================== Fixtures ====================
@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    container = DependencyContainer()

    loop = asyncio.new_event_loop()
    container.register(asyncio.AbstractEventLoop, loop)
    # 配置
    config = GlobalConfig()

    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY,
        password_file="test_password.hash"
    )
    config.ims = [
        IMConfig(
            name=TEST_ADAPTER_ID,
            enable=True,
            adapter=TEST_ADAPTER_TYPE,
            config=TEST_ADAPTER_CONFIG
        ),
        IMConfig(
            name=TEST_ADAPTER_NOT_RUNNING_ID,
            enable=False,
            adapter=TEST_ADAPTER_TYPE,
            config=TEST_ADAPTER_CONFIG
        )
    ]
    container.register(GlobalConfig, config)
    container.register(DependencyContainer, container)
    

    # 创建并注册 IMRegistry
    registry = IMRegistry()
    try:
        registry.register(TEST_ADAPTER_TYPE, DummyAdapter, DummyConfig)
    except Exception as e:
        print(e)
    container.register(IMRegistry, registry)
    
    # 创建并注册 IMManager
    manager = IMManager(container)
    container.register(IMManager, manager)
    
    manager.start_adapters(loop=loop)
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
        assert 'access_token' in data
        token = data.get('access_token')
        return {'Authorization': f'Bearer {token}'}

# ==================== 测试用例 ====================
class TestIMAdapter:
    @pytest.mark.asyncio
    async def test_get_adapter_types(self, test_client, auth_headers):
        """测试获取适配器类型列表"""
        response = await test_client.get('/api/im/types', headers=auth_headers)
        
        data = await response.get_json()
        assert 'types' in data
        assert TEST_ADAPTER_TYPE in data.get('types')
        
    @pytest.mark.asyncio
    async def test_list_adapters(self, test_client, auth_headers):
        """测试获取适配器列表"""
        response = await test_client.get('/api/im/adapters', headers=auth_headers)
        
        data = await response.get_json()
        assert 'adapters' in data
        adapters = data.get('adapters')
        assert len(adapters) == 2  # 应该有两个适配器
        adapter = next(a for a in adapters if a.get('name') == TEST_ADAPTER_ID)
        assert adapter.get('adapter') == TEST_ADAPTER_TYPE
        assert adapter.get('is_running') is True

    @pytest.mark.asyncio
    async def test_get_adapter(self, test_client, auth_headers):
        """测试获取特定适配器"""
        response = await test_client.get(
            f'/api/im/adapters/{TEST_ADAPTER_ID}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert 'adapter' in data
        adapter = data.get('adapter')
        assert adapter.get('name') == TEST_ADAPTER_ID
        assert adapter.get('adapter') == TEST_ADAPTER_TYPE
        assert adapter.get('config') == TEST_ADAPTER_CONFIG

    @pytest.mark.asyncio
    async def test_create_adapter(self, test_client, auth_headers):
        """测试创建适配器"""        
        adapter_data = IMAdapterConfig(
            name='new-adapter',
            adapter=TEST_ADAPTER_TYPE,
            config=TEST_ADAPTER_CONFIG
        )
        
        # Mock 配置文件保存
        ConfigLoader.save_config_with_backup = MagicMock()
        response = await test_client.post(
            '/api/im/adapters',
            headers=auth_headers,
            json=adapter_data.model_dump()
        )
            
        data = await response.get_json()
        assert 'adapter' in data
        adapter = data.get('adapter')
        assert adapter.get('name') == 'new-adapter'
        assert adapter.get('adapter') == TEST_ADAPTER_TYPE
        assert adapter.get('config') == TEST_ADAPTER_CONFIG
        
        # 验证配置保存
        ConfigLoader.save_config_with_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_adapter(self, test_client, auth_headers):
        """测试更新适配器"""
        adapter_data = IMAdapterConfig(
            name=TEST_ADAPTER_ID,
            adapter=TEST_ADAPTER_TYPE,
            config={'token': 'updated-token', 'name': 'Updated Bot'}
        )
        
        # Mock 配置文件保存
        ConfigLoader.save_config_with_backup = MagicMock()
        response = await test_client.put(
            f'/api/im/adapters/{TEST_ADAPTER_ID}',
            headers=auth_headers,
            json=adapter_data.model_dump()
        )
            
        data = await response.get_json()
        assert 'adapter' in data
        adapter = data.get('adapter')
        assert adapter.get('name') == TEST_ADAPTER_ID
        assert adapter.get('adapter') == TEST_ADAPTER_TYPE
        assert adapter.get('config').get('token') == 'updated-token'
        assert adapter.get('config').get('name') == 'Updated Bot'
        
        # 验证配置保存
        ConfigLoader.save_config_with_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_adapter(self, test_client, auth_headers):
        """测试停止适配器"""
        response = await test_client.post(
            f'/api/im/adapters/{TEST_ADAPTER_ID}/stop',
            headers=auth_headers
        )
        data = await response.get_json()
        assert 'message' in data
        assert data.get('message') == 'Adapter stopped successfully'
        
        # 验证适配器状态
        response = await test_client.get(
            f'/api/im/adapters/{TEST_ADAPTER_ID}',
            headers=auth_headers
        )
        data = await response.get_json()
        assert 'adapter' in data
        assert data.get('adapter').get('is_running') is False 
        
    @pytest.mark.asyncio
    async def test_start_adapter(self, test_client, auth_headers):
        """测试启动适配器"""
        response = await test_client.post(
            f'/api/im/adapters/{TEST_ADAPTER_ID}/start',
            headers=auth_headers
        )
        data = await response.get_json()
        assert 'message' in data
        assert data.get('message') == 'Adapter started successfully'

        # 验证适配器状态
        response = await test_client.get(
            f'/api/im/adapters/{TEST_ADAPTER_ID}',
            headers=auth_headers
        )
        data = await response.get_json()
        assert 'adapter' in data
        assert data.get('adapter').get('is_running') is True
    
    @pytest.mark.asyncio
    async def test_delete_adapter(self, test_client, auth_headers):
        """测试删除适配器"""
        # 先启动适配器
        await test_client.post(
            f'/api/im/adapters/{TEST_ADAPTER_ID}/start',
            headers=auth_headers
        )
        
        # Mock 配置文件保存
        ConfigLoader.save_config_with_backup = MagicMock()
        response = await test_client.delete(
            f'/api/im/adapters/{TEST_ADAPTER_ID}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert 'message' in data
        assert data.get('message') == 'Adapter deleted successfully'
        
        # 验证配置保存
        ConfigLoader.save_config_with_backup.assert_called_once()
