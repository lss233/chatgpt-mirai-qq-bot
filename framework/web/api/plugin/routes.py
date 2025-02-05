from quart import Blueprint, g, jsonify
from ...auth.middleware import require_auth
from framework.plugin_manager.models import PluginInfo
from framework.plugin_manager.plugin_loader import PluginLoader
from framework.config.global_config import GlobalConfig

plugin_bp = Blueprint('plugin', __name__)

@plugin_bp.route('/<plugin_name>', methods=['GET'])
@require_auth
async def get_plugin_details(plugin_name: str):
    """获取插件详细信息"""
    loader: PluginLoader = g.container.resolve(PluginLoader)
    
    plugin_info = loader.get_plugin_info(plugin_name)
    if not plugin_info:
        return jsonify({"error": "Plugin not found"}), 404
    
    return {"plugin": plugin_info.model_dump()}

@plugin_bp.route('/update/<plugin_name>', methods=['POST'])
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
        # TODO: 实现插件更新逻辑
        return {"plugin": plugin_info.model_dump()}
    except Exception as e:
        return jsonify({"error": str(e)}), 500