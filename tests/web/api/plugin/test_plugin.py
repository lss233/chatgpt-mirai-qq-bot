from unittest.mock import patch, MagicMock, mock_open
import pytest
from datetime import datetime, timedelta

import pytest_asyncio
from framework.plugin_manager.models import PluginInfo
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig, PluginConfig
from framework.plugin_manager.plugin import Plugin
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.plugin_manager.plugin_event_bus import PluginEventBus
from framework.llm.llm_registry import LLMBackendRegistry
from framework.im.im_registry import IMRegistry
from framework.im.manager import IMManager
from framework.workflow.core.dispatch import WorkflowDispatcher
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry
from framework.workflow.core.workflow.registry import WorkflowRegistry
from framework.config.config_loader import ConfigLoader
from tests.utils.auth_test_utils import setup_auth_service, auth_headers

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_PLUGIN_NAME = "test-plugin"

# ==================== 测试用插件 ====================
class TestPlugin(Plugin):
    """测试用插件"""
    __test__ = False
    
    def __init__(self):
        self.initialized = False
        self.started = False
        
    def on_load(self):
        self.initialized = True
        
    def on_start(self):
        self.started = True
        
    def on_stop(self):
        self.started = False

# ==================== Fixtures ====================
@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    container.register(DependencyContainer, container)
    
    # 配置
    config = GlobalConfig()
    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY,
        password_file="test_password.hash"
    )
    config.plugins = PluginConfig(
        enable=[TEST_PLUGIN_NAME]
    )
    container.register(GlobalConfig, config)
    
    # 设置认证服务
    setup_auth_service(container)
    
    # 注册必要的组件
    container.register(LLMBackendRegistry, LLMBackendRegistry())
    container.register(IMRegistry, IMRegistry())
    container.register(IMManager, IMManager(container))
    container.register(WorkflowRegistry, WorkflowRegistry(container))
    container.register(DispatchRuleRegistry, DispatchRuleRegistry(container))
    container.register(WorkflowDispatcher, WorkflowDispatcher(container))
    container.register(PluginEventBus, PluginEventBus())
    
    # 创建插件加载器并注册测试插件
    plugin_loader = PluginLoader(container, "plugins")
    plugin_loader.register_plugin(TestPlugin, TEST_PLUGIN_NAME)
    container.register(PluginLoader, plugin_loader)
    
    app = create_app(container)
    app.container = container
    return app

@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return app.test_client()

# ==================== 测试用例 ====================
class TestPlugin:
    @pytest.mark.asyncio
    async def test_get_plugin_details(self, test_client, auth_headers):
        """测试获取插件详情"""
        response = await test_client.get(
            f'/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert "error" not in data
        assert 'plugin' in data
        plugin = data['plugin']
        assert plugin['name'] == 'TestPlugin'
        assert plugin['is_internal'] is True
        assert plugin['is_enabled'] is True
        
    @pytest.mark.asyncio
    async def test_get_nonexistent_plugin(self, test_client, auth_headers):
        """测试获取不存在的插件"""
        response = await test_client.get(
            '/backend-api/api/plugin/plugins/nonexistent',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = await response.get_json()
        assert 'error' in data
        
    @pytest.mark.asyncio
    async def test_update_plugin(self, test_client, auth_headers):
        """测试更新插件"""
        # 由于是内部插件，更新应该失败
        response = await test_client.put(
            f'/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}',
            headers=auth_headers
        )
        
        assert response.status_code == 400  # 内部插件不支持更新
        data = await response.get_json()
        assert 'error' in data

    @pytest.mark.asyncio
    async def test_enable_plugin(self, test_client, auth_headers):
        """测试启用插件"""
        # Mock 配置文件保存
        with patch("framework.config.config_loader.ConfigLoader.save_config_with_backup") as mock_save:
            response = await test_client.post(
                f'/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}/enable',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "error" not in data
            assert data['plugin']['is_enabled'] is True
            
    @pytest.mark.asyncio
    async def test_disable_plugin(self, test_client, auth_headers):
        """测试禁用插件"""
        # Mock 配置文件保存
        with patch("framework.config.config_loader.ConfigLoader.save_config_with_backup") as mock_save:
            response = await test_client.post(
                f'/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}/disable',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "error" not in data
            assert data['plugin']['is_enabled'] is False
            
            # 验证配置保存
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_plugin(self, test_client, auth_headers):
        """测试安装插件"""
        with patch("framework.web.api.plugin.routes.PluginLoader.install_plugin") as mock_install_plugin:   
            mock_install_plugin.return_value = PluginInfo(
                name="test-plugin",
                package_name="test-plugin-package",
                description="test-plugin-description",
                is_internal=False,
                is_enabled=False,
                version="1.0.0",
                author="test-author"
            )
            
            # Mock 配置文件保存
            with patch("framework.config.config_loader.ConfigLoader.save_config_with_backup") as mock_save:
                response = await test_client.post(
                    '/backend-api/api/plugin/plugins',
                    headers=auth_headers,
                    json={
                        'package_name': 'test-plugin-package',
                        'version': '1.0.0'
                    }
                )
                
                data = await response.get_json()
                assert "error" not in data
                assert data['plugin']['package_name'] == 'test-plugin-package'
                
                # 验证配置保存
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, test_client, auth_headers):
        """测试卸载插件"""
        # 由于是内部插件，卸载应该失败
        response = await test_client.delete(
            f'/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert 'error' in data 
        assert response.status_code == 400  # 内部插件不能卸载