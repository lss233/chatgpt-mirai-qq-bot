import pytest
from unittest.mock import Mock, patch
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.plugin_manager.models import PluginInfo

@pytest.fixture
def plugin_loader():
    return PluginLoader("plugins")

@pytest.mark.asyncio
async def test_install_plugin(plugin_loader):
    # 模拟成功安装插件
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        with patch("importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.__plugin_info__ = {
                "name": "Test Plugin",
                "package_name": "test-plugin",
                "description": "Test plugin",
                "version": "1.0.0",
                "author": "Tester"
            }
            mock_import.return_value = mock_module
            
            plugin_info = await plugin_loader.install_plugin("test-plugin")
            assert plugin_info is not None
            assert plugin_info.name == "Test Plugin"
            assert plugin_info.package_name == "test-plugin"
            assert plugin_info.version == "1.0.0"

@pytest.mark.asyncio
async def test_install_plugin_with_version(plugin_loader):
    # 测试指定版本安装
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        with patch("importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.__plugin_info__ = {
                "name": "Test Plugin",
                "package_name": "test-plugin",
                "description": "Test plugin",
                "version": "1.0.0",
                "author": "Tester"
            }
            mock_import.return_value = mock_module
            
            plugin_info = await plugin_loader.install_plugin("test-plugin", "1.0.0")
            assert plugin_info is not None
            assert plugin_info.version == "1.0.0"

@pytest.mark.asyncio
async def test_install_plugin_failure(plugin_loader):
    # 测试安装失败
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.communicate.return_value = (b"", b"Installation failed")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        with pytest.raises(Exception) as exc_info:
            await plugin_loader.install_plugin("test-plugin")
        assert "Failed to install plugin" in str(exc_info.value)

@pytest.mark.asyncio
async def test_uninstall_plugin(plugin_loader):
    # 模拟成功卸载插件
    plugin_info = PluginInfo(
        name="Test Plugin",
        package_name="test-plugin",
        description="Test plugin",
        version="1.0.0",
        author="Tester",
        is_internal=False
    )
    plugin_loader.plugins["test-plugin"] = plugin_info
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        result = await plugin_loader.uninstall_plugin("test-plugin")
        assert result is True
        assert "test-plugin" not in plugin_loader.plugins

@pytest.mark.asyncio
async def test_uninstall_internal_plugin(plugin_loader):
    # 测试卸载内部插件
    plugin_info = PluginInfo(
        name="Internal Plugin",
        package_name="internal-plugin",
        description="Internal plugin",
        version="1.0.0",
        author="System",
        is_internal=True
    )
    plugin_loader.plugins["internal-plugin"] = plugin_info
    
    with pytest.raises(Exception) as exc_info:
        await plugin_loader.uninstall_plugin("internal-plugin")
    assert "Cannot uninstall internal plugin" in str(exc_info.value)

@pytest.mark.asyncio
async def test_enable_plugin(plugin_loader):
    # 测试启用插件
    plugin_info = PluginInfo(
        name="Test Plugin",
        package_name="test-plugin",
        description="Test plugin",
        version="1.0.0",
        author="Tester",
        is_enabled=False
    )
    plugin_loader.plugins["test-plugin"] = plugin_info
    
    with patch("importlib.import_module") as mock_import:
        mock_module = Mock()
        mock_import.return_value = mock_module
        
        result = await plugin_loader.enable_plugin("test-plugin")
        assert result is True
        assert plugin_info.is_enabled is True

@pytest.mark.asyncio
async def test_disable_plugin(plugin_loader):
    # 测试禁用插件
    plugin_info = PluginInfo(
        name="Test Plugin",
        package_name="test-plugin",
        description="Test plugin",
        version="1.0.0",
        author="Tester",
        is_enabled=True
    )
    plugin_loader.plugins["test-plugin"] = plugin_info
    plugin_loader.loaded_modules["test-plugin"] = Mock()
    
    result = await plugin_loader.disable_plugin("test-plugin")
    assert result is True
    assert plugin_info.is_enabled is False

@pytest.mark.asyncio
async def test_update_plugin(plugin_loader):
    # 测试更新插件
    plugin_info = PluginInfo(
        name="Test Plugin",
        package_name="test-plugin",
        description="Test plugin",
        version="1.0.0",
        author="Tester",
        is_internal=False
    )
    plugin_loader.plugins["test-plugin"] = plugin_info
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        with patch("importlib.reload") as mock_reload:
            mock_module = Mock()
            mock_module.__plugin_info__ = {
                "name": "Test Plugin",
                "package_name": "test-plugin",
                "description": "Test plugin",
                "version": "1.1.0",
                "author": "Tester"
            }
            mock_reload.return_value = mock_module
            
            updated_info = await plugin_loader.update_plugin("test-plugin")
            assert updated_info is not None
            assert updated_info.version == "1.1.0"

@pytest.mark.asyncio
async def test_update_internal_plugin(plugin_loader):
    # 测试更新内部插件
    plugin_info = PluginInfo(
        name="Internal Plugin",
        package_name="internal-plugin",
        description="Internal plugin",
        version="1.0.0",
        author="System",
        is_internal=True
    )
    plugin_loader.plugins["internal-plugin"] = plugin_info
    
    with pytest.raises(Exception) as exc_info:
        await plugin_loader.update_plugin("internal-plugin")
    assert "Cannot update internal plugin" in str(exc_info.value) 