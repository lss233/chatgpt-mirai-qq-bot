from quart import Blueprint, g, jsonify, request
import aiohttp
from packaging.version import Version

from framework.logger import get_logger
from ...auth.middleware import require_auth
from framework.plugin_manager.models import PluginInfo
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.config.global_config import GlobalConfig
from framework.config.config_loader import ConfigLoader
from .models import InstallPluginRequest, PluginList, PluginResponse

plugin_bp = Blueprint('plugin', __name__)

logger = get_logger("WebServer")

def is_upgradable(installed_version: str, market_version: str) -> bool:
    """检查插件是否可升级"""
    try:
        return Version(market_version) > Version(installed_version)
    except ValueError:
        return False

async def fetch_from_market(path: str, params: dict = None) -> dict:
    """从插件市场获取数据的通用方法"""
    plugin_market_base_url = g.container.resolve(GlobalConfig).plugins.market_base_url
    async with aiohttp.ClientSession(trust_env=True) as session:
        url = f"{plugin_market_base_url}/{path}"
        logger.info(f"Fetching from market: {url}")
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"插件市场请求失败: {response.status}")
            return await response.json()

async def enrich_plugin_data(plugins: list, loader: PluginLoader) -> list:
    """为插件数据添加安装状态和可升级状态"""
    installed_plugins = loader.get_all_plugin_infos()
    
    for plugin in plugins:
        installed_plugin = next(
            (p for p in installed_plugins if p.package_name == plugin['pypiPackage']),
            None
        )
        
        plugin['isInstalled'] = installed_plugin is not None
        plugin['installedVersion'] = installed_plugin.version if installed_plugin else None
        plugin['isUpgradable'] = (
            is_upgradable(installed_plugin.version, plugin['pypiInfo']['version'])
            if installed_plugin
            else False
        )
        plugin['isEnabled'] = installed_plugin.is_enabled if installed_plugin else False
    
    return plugins

@plugin_bp.route('/v1/search', methods=['GET'])
@require_auth
async def search_plugins():
    """搜索插件市场"""
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    
    try:
        result = await fetch_from_market('search', {
            'query': query,
            'page': page,
            'pageSize': page_size
        })
        
        # 添加安装状态和可升级状态
        loader: PluginLoader = g.container.resolve(PluginLoader)
        result['plugins'] = await enrich_plugin_data(result['plugins'], loader)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/v1/info/<plugin_name>', methods=['GET'])
@require_auth
async def get_market_plugin_info(plugin_name: str):
    """获取插件市场中插件的详细信息"""
    try:
        result = await fetch_from_market(f'info/{plugin_name}')
        
        # 添加安装状态和可升级状态
        loader: PluginLoader = g.container.resolve(PluginLoader)
        result = (await enrich_plugin_data([result], loader))[0]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/plugins', methods=['GET'])
@require_auth
async def list_plugins():
    """获取所有已安装的插件列表"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    plugins = loader.get_all_plugin_infos()
    return PluginList(plugins=plugins).model_dump()

@plugin_bp.route('/plugins/<plugin_name>', methods=['GET'])
@require_auth
async def get_plugin_details(plugin_name: str):
    """获取已安装插件的详细信息"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    print(f"Getting plugin details for {plugin_name}")
    print(loader.plugin_infos)
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    return PluginResponse(plugin=plugin_info).model_dump()

@plugin_bp.route('/plugins', methods=['POST'])
@require_auth
async def install_plugin():
    """安装新插件"""
    data = await request.get_json()
    install_data = InstallPluginRequest(**data)
    
    loader: PluginLoader = g.container.resolve(PluginLoader)
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    try:
        # 安装插件
        plugin_info = await loader.install_plugin(install_data.package_name, install_data.version)
        if not plugin_info:
            return jsonify({"error": "Failed to install plugin"}), 500
            
        # 更新配置
        if plugin_info.package_name not in config.plugins.enable:
            config.plugins.enable.append(plugin_info.package_name)
            ConfigLoader.save_config_with_backup("config.yaml", config)
        
        return PluginResponse(plugin=plugin_info).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/plugins/<plugin_name>', methods=['DELETE'])
@require_auth
async def uninstall_plugin(plugin_name: str):
    """卸载插件"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    # 检查插件是否存在
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    # 内部插件不能卸载
    if plugin_info.is_internal:
        return jsonify({"error": "Cannot uninstall internal plugin"}), 400
    
    try:
        # 卸载插件
        await loader.uninstall_plugin(plugin_name)
        
        # 更新配置
        if plugin_info.package_name in config.plugins.enable:
            config.plugins.enable.remove(plugin_info.package_name)
            ConfigLoader.save_config_with_backup("config.yaml", config)
        
        return jsonify({"message": "Plugin uninstalled successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/plugins/<plugin_name>/enable', methods=['POST'])
@require_auth
async def enable_plugin(plugin_name: str):
    """启用插件"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    # 检查插件是否存在
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    try:
        # 启用插件
        await loader.enable_plugin(plugin_name)
        
        # 更新配置
        if plugin_name and plugin_name not in config.plugins.enable and not plugin_info.is_internal:
            config.plugins.enable.append(plugin_name)
        ConfigLoader.save_config_with_backup("config.yaml", config)
        
        return PluginResponse(plugin=plugin_info).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/plugins/<plugin_name>/disable', methods=['POST'])
@require_auth
async def disable_plugin(plugin_name: str):
    """禁用插件"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    # 检查插件是否存在
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    try:
        # 禁用插件
        await loader.disable_plugin(plugin_name)
        
        # 更新配置
        if plugin_name and plugin_name in config.plugins.enable and not plugin_info.is_internal:
            config.plugins.enable.remove(plugin_name)
            
        ConfigLoader.save_config_with_backup("config.yaml", config)

        return PluginResponse(plugin=plugin_info).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plugin_bp.route('/plugins/<plugin_name>', methods=['PUT'])
@require_auth
async def update_plugin(plugin_name: str):
    """更新插件到最新版本"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    
    # 检查插件是否存在
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    # 内部插件不支持更新
    if plugin_info.is_internal:
        return jsonify({"error": "Cannot update internal plugin"}), 400
    
    try:
        # 执行更新
        updated_info = await loader.update_plugin(plugin_name)
        if not updated_info:
            return jsonify({"error": "Failed to update plugin"}), 500
            
        return PluginResponse(plugin=updated_info).model_dump()
    except Exception as e:
        return jsonify({"error": str(e)}), 500