import asyncio
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

from packaging import version
from quart import Blueprint, current_app, g, request, websocket

from kirara_ai.config.config_loader import CONFIG_FILE, ConfigLoader
from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.im.manager import IMManager
from kirara_ai.internal import set_restart_flag, shutdown_event
from kirara_ai.llm.llm_manager import LLMManager
from kirara_ai.logger import WebSocketLogHandler, get_logger
from kirara_ai.plugin_manager.plugin_loader import PluginLoader
from kirara_ai.plugin_manager.utils import build_package_manager_command
from kirara_ai.web.api.system.utils import (download_file, get_cpu_info, get_cpu_usage, get_installed_version,
                                            get_latest_npm_version, get_latest_pypi_version, get_memory_usage)
from kirara_ai.web.auth.services import AuthService
from kirara_ai.workflow.core.workflow import WorkflowRegistry

from ...auth.middleware import require_auth
from .models import SystemStatus, SystemStatusResponse, UpdateCheckResponse

system_bp = Blueprint("system", __name__)

# 记录启动时间
start_time = time.time()

# 获取系统日志记录器
logger = get_logger("System-API")

@system_bp.websocket('/logs')
async def logs_websocket():
    """WebSocket端点，用于实时推送日志"""
    try:
        token_data = await websocket.receive()
        
        token = json.loads(token_data)["token"]
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    auth_service: AuthService = g.container.resolve(AuthService)
    if not auth_service.verify_token(token):
        await websocket.close(code=1008, reason="Invalid token")
        return
    try:

        # 将当前WebSocket连接添加到日志处理器
        WebSocketLogHandler.add_websocket(websocket._get_current_object(), asyncio.get_event_loop())
        
        # 保持连接打开，直到客户端断开
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
    finally:
        # 从日志处理器中移除当前连接
        WebSocketLogHandler.remove_websocket(websocket._get_current_object())

@system_bp.route("/config", methods=["GET"])
@require_auth
async def get_system_config():
    """获取系统配置"""
    try:
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        return {
            "web": {
                "host": config.web.host,
                "port": config.web.port
            },
            "plugins": {
                "market_base_url": config.plugins.market_base_url
            },
            "update": {
                "pypi_registry": config.update.pypi_registry,
                "npm_registry": config.update.npm_registry
            },
            "system": {
                "timezone": config.system.timezone
            },
            "tracing": {
                "llm_tracing_content": config.tracing.llm_tracing_content
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500

@system_bp.route("/config/web", methods=["POST"])
@require_auth
async def update_web_config():
    """更新Web配置"""
    try:
        data = await request.get_json()
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        
        config.web.host = data["host"]
        config.web.port = data["port"]
        
        # 保存配置
        ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
        return {"status": "success", "restart_required": True}
    except Exception as e:
        return {"error": str(e)}, 500

@system_bp.route("/config/plugins", methods=["POST"])
@require_auth
async def update_plugins_config():
    """更新插件配置"""
    try:
        data = await request.get_json()
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        
        config.plugins.market_base_url = data["market_base_url"]
        
        # 保存配置
        ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500

@system_bp.route("/config/update", methods=["POST"])
@require_auth
async def update_registry_config():
    """更新更新源配置"""
    try:
        data = await request.get_json()
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        
        if not hasattr(config, "update"):
            config.update = {}
        
        config.update.pypi_registry = data["pypi_registry"]
        config.update.npm_registry = data["npm_registry"]
        
        # 保存配置
        ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500

@system_bp.route("/config/system", methods=["POST"])
@require_auth
async def update_system_config():
    """更新系统配置"""
    try:
        data = await request.get_json()
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        
        # 检查时区是否变化
        timezone_changed = False
        if "timezone" in data and data["timezone"] != config.system.timezone:
            config.system.timezone = data["timezone"]
            timezone_changed = True
        
        # 保存配置
        ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
        
        # 如果时区变化，设置系统时区并调用 tzset
        if timezone_changed and hasattr(time, "tzset"):
            os.environ["TZ"] = config.system.timezone
            time.tzset()
            
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500
    
@system_bp.route("/config/tracing", methods=["POST"])
@require_auth
async def update_tracing_config():
    """更新追踪配置"""
    try:
        data = await request.get_json()
        config: GlobalConfig = g.container.resolve(GlobalConfig)
        
        config.tracing.llm_tracing_content = data["llm_tracing_content"]
        
        # 保存配置
        ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500


@system_bp.route("/status", methods=["GET"])
@require_auth
async def get_system_status():
    """获取系统状态"""
    im_manager: IMManager = g.container.resolve(IMManager)
    llm_manager: LLMManager = g.container.resolve(LLMManager)
    plugin_loader: PluginLoader = g.container.resolve(PluginLoader)
    workflow_registry: WorkflowRegistry = g.container.resolve(WorkflowRegistry)

    # 计算运行时间
    uptime = time.time() - start_time

    # 获取活跃的适配器数量
    active_adapters = len(
        [adapter for adapter in im_manager.adapters.values() if adapter.is_running]
    )

    # 获取活跃的LLM后端数量
    active_backends = len(llm_manager.active_backends)

    # 获取已加载的插件数量
    loaded_plugins = len(plugin_loader.plugins)

    # 获取工作流数量
    workflow_count = len(workflow_registry._workflows)

    # 获取系统资源使用情况
    memory_usage = get_memory_usage()
    cpu_usage = get_cpu_usage()
    
    # 检测代理服务
    has_proxy = bool(os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY') or 
                    os.environ.get('http_proxy') or os.environ.get('https_proxy'))

    # 获取CPU信息
    cpu_info = get_cpu_info()

    # 获取Python版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # 获取平台信息
    platform_info = f"{sys.platform}"

    status = SystemStatus(
        uptime=uptime,
        active_adapters=active_adapters,
        active_backends=active_backends,
        loaded_plugins=loaded_plugins,
        workflow_count=workflow_count,
        memory_usage=memory_usage,
        cpu_usage=cpu_usage,
        version=get_installed_version(),
        platform=platform_info,
        cpu_info=cpu_info,
        python_version=python_version,
        has_proxy=has_proxy,
    )

    return SystemStatusResponse(status=status).model_dump()


@system_bp.route("/check-update", methods=["GET"])
@require_auth
async def check_update():
    """检查系统更新"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    npm_registry = config.update.npm_registry
    
    current_backend_version = get_installed_version()
    latest_backend_version, backend_download_url = await get_latest_pypi_version("kirara-ai")
    
    # 获取前端最新版本信息，但不判断是否需要更新
    latest_webui_version, webui_download_url = await get_latest_npm_version("kirara-ai-webui", npm_registry)
    
    # 只判断后端是否需要更新
    backend_update_available = version.parse(latest_backend_version) > version.parse(current_backend_version)
    
    return UpdateCheckResponse(
        current_backend_version=current_backend_version,
        latest_backend_version=latest_backend_version,
        backend_update_available=backend_update_available,
        backend_download_url=backend_download_url,
        latest_webui_version=latest_webui_version,
        webui_download_url=webui_download_url
    ).model_dump()


@system_bp.route("/update", methods=["POST"])
@require_auth
async def perform_update():
    """执行更新操作"""
    data = await request.get_json()
    update_backend = data.get("update_backend", False)
    update_webui = data.get("update_webui", False)
    temp_dir = tempfile.mkdtemp()
    
    try:
        if update_backend:
            backend_url = data["backend_download_url"]
            backend_file, backend_hash = await download_file(backend_url, temp_dir)
            # 安装后端
            subprocess.run(build_package_manager_command("install", backend_file), check=True)
        
        if update_webui:
            webui_url = data["webui_download_url"]
            webui_file, webui_hash = await download_file(webui_url, temp_dir)
            # 解压并安装前端
            static_dir = current_app.static_folder or "web"
            with tarfile.open(webui_file, "r:gz") as tar:
                # 解压 package/dist 里的所有文件到 web 目录
                for member in tar.getmembers():
                    if member.name.startswith("package/dist/"):
                        # 去掉 "package/dist/" 前缀
                        member.name = member.name[len("package/dist/"):]
                        # 解压到 static 目录
                        tar.extract(member, path=static_dir)
        
        return {"status": "success", "message": "更新完成"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    
    finally:
        shutil.rmtree(temp_dir)


@system_bp.route("/restart", methods=["POST"])
@require_auth
async def restart_system():
    """重启系统"""
    # 记录重启日志，会通过WebSocket发送给所有客户端
    logger.warning("服务器即将重启，请稍候...")
    
    # 设置重启标志
    set_restart_flag()
    shutdown_event.set()
    return {"status": "success", "message": "重启请求已发送"}
