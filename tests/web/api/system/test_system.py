import pytest
from unittest.mock import patch, MagicMock

import pytest_asyncio
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig
from framework.im.manager import IMManager
from framework.llm.llm_manager import LLMManager
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.workflow.core.workflow import WorkflowRegistry

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"

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
    
    # Mock其他依赖
    im_manager = MagicMock(spec=IMManager)
    im_manager.adapters = [MagicMock(is_running=True), MagicMock(is_running=False)]
    container.register(IMManager, im_manager)
    
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.active_backends = {'backend1': [], 'backend2': []}
    container.register(LLMManager, llm_manager)
    
    plugin_loader = MagicMock(spec=PluginLoader)
    plugin_loader.plugins = [MagicMock(), MagicMock(), MagicMock()]
    container.register(PluginLoader, plugin_loader)
    
    workflow_registry = MagicMock(spec=WorkflowRegistry)
    workflow_registry._workflows = {'workflow1': MagicMock(), 'workflow2': MagicMock()}
    container.register(WorkflowRegistry, workflow_registry)
    
    app = create_app(container)
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
        token = data['access_token']
        return {'Authorization': f'Bearer {token}'}

# ==================== 测试用例 ====================
class TestSystemStatus:
    @pytest.mark.asyncio
    async def test_get_system_status(self, test_client, auth_headers):
        """测试获取系统状态"""
        # Mock psutil.Process
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1024*1024*100, vms=1024*1024*500)
        mock_process.memory_percent.return_value = 2.5
        mock_process.cpu_percent.return_value = 1.2
        
        with patch('framework.web.api.system.routes.psutil.Process', return_value=mock_process):
            response = await test_client.get('/api/system/status', headers=auth_headers)
            
            assert response.status_code == 200
            data = await response.get_json()
            
            assert 'status' in data
            status = data['status']
            
            # 验证基本字段
            assert 'version' in status
            assert 'uptime' in status
            assert status['active_adapters'] == 1  # 只有一个运行中的适配器
            assert status['active_backends'] == 2  # 两个后端
            assert status['loaded_plugins'] == 3  # 三个插件
            assert status['workflow_count'] == 2  # 两个工作流
            
            # 验证资源使用情况
            assert 'memory_usage' in status
            assert 'cpu_usage' in status
            assert status['memory_usage']['rss'] == 100  # 100MB
            assert status['memory_usage']['vms'] == 500  # 500MB
            assert status['memory_usage']['percent'] == 2.5
            assert status['cpu_usage'] == 1.2

    @pytest.mark.asyncio
    async def test_get_system_status_unauthorized(self, test_client):
        """测试未认证时获取系统状态"""
        response = await test_client.get('/api/system/status')
        
        assert response.status_code == 401
        data = await response.get_json()
        assert 'error' in data 