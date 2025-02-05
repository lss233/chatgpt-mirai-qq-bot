from quart import Blueprint, g, jsonify, request
from ...auth.middleware import require_auth
from framework.plugin_manager.models import PluginInfo
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.config.global_config import GlobalConfig
from framework.config.config_loader import ConfigLoader
from .models import InstallPluginRequest, PluginList, PluginResponse

plugin_bp = Blueprint('plugin', __name__)

@plugin_bp.route('/plugins', methods=['GET'])
@require_auth
async def list_plugins():
    """获取所有插件列表"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    plugins = loader.get_all_plugin_infos()
    return PluginList(plugins=plugins).model_dump()

@plugin_bp.route('/plugins/<plugin_name>', methods=['GET'])
@require_auth
async def get_plugin_details(plugin_name: str):
    """获取插件详细信息"""
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
        if plugin_info.package_name and plugin_info.package_name not in config.plugins.enable:
            config.plugins.enable.append(plugin_info.package_name)
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
        if plugin_info.package_name and plugin_info.package_name in config.plugins.enable:
            config.plugins.enable.remove(plugin_info.package_name)
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