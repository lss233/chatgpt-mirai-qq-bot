from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from kirara_ai.config.global_config import GlobalConfig, PluginConfig, WebConfig
from kirara_ai.im.im_registry import IMRegistry
from kirara_ai.im.manager import IMManager
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.llm_registry import LLMBackendRegistry
from kirara_ai.plugin_manager.models import PluginInfo
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.plugin_manager.plugin_event_bus import PluginEventBus
from kirara_ai.plugin_manager.plugin_loader import PluginLoader
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.block import BlockRegistry
from kirara_ai.workflow.core.dispatch import WorkflowDispatcher
from kirara_ai.workflow.core.dispatch.registry import DispatchRuleRegistry
from kirara_ai.workflow.core.workflow.registry import WorkflowRegistry
from tests.utils.auth_test_utils import auth_headers, setup_auth_service  # noqa
from tests.utils.test_block_registry import create_test_block_registry

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_PLUGIN_NAME = "test-plugin"


# ==================== 测试用插件 ====================
def make_test_plugin():
    class TestPlugin(Plugin):
        """测试用插件"""

        __test__ = True

        def __init__(self):
            self.initialized = False
            self.started = False

        def on_load(self):
            self.initialized = True

        def on_start(self):
            self.started = True

        def on_stop(self):
            self.started = False

    return TestPlugin


# ==================== Mock 数据 ====================
async def MOCK_PLUGIN_SEARCH_RESPONSE():
    return {
        "plugins": [
            {
                "name": "测试插件",
                "description": "测试插件描述",
                "author": "测试作者",
                "pypiPackage": "test-plugin",
                "pypiInfo": {
                    "version": "0.1.0",
                    "description": "PyPI 描述",
                    "author": "PyPI 作者",
                    "homePage": "https://example.com",
                },
                "isInstalled": True,
                "installedVersion": "1.0.0",
                "isUpgradable": False,
                "isEnabled": True,
                "requiresRestart": False,
            }
        ],
        "totalCount": 1,
        "totalPages": 1,
        "page": 1,
        "pageSize": 10,
    }


async def MOCK_PLUGIN_INFO_RESPONSE():
    return {
        "name": "测试插件",
        "description": "测试插件描述",
        "author": "测试作者",
        "pypiPackage": "test-plugin",
        "pypiInfo": {
            "version": "0.1.0",
            "description": "PyPI 描述",
            "author": "PyPI 作者",
            "homePage": "https://example.com",
        },
        "isInstalled": True,
        "installedVersion": "1.0.0",
        "isUpgradable": False,
        "isEnabled": True,
    }


# ==================== Fixtures ====================
@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    container.register(DependencyContainer, container)

    # 配置
    config = GlobalConfig()
    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY, password_file="test_password.hash"
    )
    config.plugins = PluginConfig(enable=[TEST_PLUGIN_NAME])
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
    container.register(BlockRegistry, create_test_block_registry())

    # 创建插件加载器并注册测试插件
    plugin_loader = PluginLoader(container, "plugins")
    plugin_loader.register_plugin(make_test_plugin(), TEST_PLUGIN_NAME)
    container.register(PluginLoader, plugin_loader)

    web_server = WebServer(container)
    container.register(WebServer, web_server)
    return web_server.app


@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return TestClient(app)


# ==================== 测试用例 ====================
class TestPlugin:
    @pytest.mark.asyncio
    async def test_search_plugins(self, test_client, auth_headers):
        """测试搜索插件市场"""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json.return_value = MOCK_PLUGIN_SEARCH_RESPONSE()
            mock_get.return_value.__aenter__.return_value = mock_response

            response = test_client.get(
                "/backend-api/api/plugin/v1/search?query=test&page=1&pageSize=10",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data == await MOCK_PLUGIN_SEARCH_RESPONSE()

    @pytest.mark.asyncio
    async def test_get_plugin_info(self, test_client, auth_headers):
        """测试获取插件详情"""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json.return_value = MOCK_PLUGIN_INFO_RESPONSE()
            mock_get.return_value.__aenter__.return_value = mock_response

            response = test_client.get(
                f"/backend-api/api/plugin/v1/info/{TEST_PLUGIN_NAME}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            del data["requiresRestart"]
            assert data == await MOCK_PLUGIN_INFO_RESPONSE()

    @pytest.mark.asyncio
    async def test_get_plugin_details(self, test_client, auth_headers):
        """测试获取插件详情"""
        response = test_client.get(
            f"/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}", headers=auth_headers
        )

        data = response.json()
        assert "error" not in data
        assert "plugin" in data
        plugin = data["plugin"]
        assert plugin["name"] == "TestPlugin"
        assert plugin["is_internal"] is True
        assert plugin["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_plugin(self, test_client, auth_headers):
        """测试获取不存在的插件"""
        response = test_client.get(
            "/backend-api/api/plugin/plugins/nonexistent", headers=auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_update_plugin(self, test_client, auth_headers):
        """测试更新插件"""
        # 由于是内部插件，更新应该失败
        response = test_client.put(
            f"/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}", headers=auth_headers
        )

        assert response.status_code == 400  # 内部插件不支持更新
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_enable_plugin(self, test_client, auth_headers):
        """测试启用插件"""
        # Mock 配置文件保存
        with patch(
            "kirara_ai.config.config_loader.ConfigLoader.save_config_with_backup"
        ) as mock_save:
            response = test_client.post(
                f"/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}/enable",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "error" not in data
            assert data["plugin"]["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_disable_plugin(self, test_client, auth_headers):
        """测试禁用插件"""
        # Mock 配置文件保存
        with patch(
            "kirara_ai.config.config_loader.ConfigLoader.save_config_with_backup"
        ) as mock_save:
            response = test_client.post(
                f"/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}/disable",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "error" not in data
            assert data["plugin"]["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_install_plugin(self, test_client, auth_headers):
        """测试安装插件"""
        with patch(
            "kirara_ai.web.api.plugin.routes.PluginLoader.install_plugin"
        ) as mock_install_plugin:
            mock_install_plugin.return_value = PluginInfo(
                name="test-plugin",
                package_name="test-plugin-package",
                description="test-plugin-description",
                is_internal=False,
                is_enabled=False,
                version="1.0.0",
                author="test-author",
            )

            # Mock 配置文件保存
            with patch(
                "kirara_ai.config.config_loader.ConfigLoader.save_config_with_backup"
            ) as mock_save:
                response = test_client.post(
                    "/backend-api/api/plugin/plugins",
                    headers=auth_headers,
                    json={"package_name": "test-plugin-package", "version": "1.0.0"},
                )

                data = response.json()
                assert "error" not in data
                assert data["plugin"]["package_name"] == "test-plugin-package"

                # 验证配置保存
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, test_client, auth_headers):
        """测试卸载插件"""
        # 由于是内部插件，卸载应该失败
        response = test_client.delete(
            f"/backend-api/api/plugin/plugins/{TEST_PLUGIN_NAME}", headers=auth_headers
        )

        data = response.json()
        assert "error" in data
        assert response.status_code == 400  # 内部插件不能卸载
