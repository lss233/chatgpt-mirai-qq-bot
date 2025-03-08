import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

import aiohttp
import psutil
from packaging import version
from quart import Blueprint, current_app, g, request

from kirara_ai.config.config_loader import CONFIG_FILE, ConfigLoader
from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.im.manager import IMManager
from kirara_ai.llm.llm_manager import LLMManager
from kirara_ai.plugin_manager.plugin_loader import PluginLoader
from kirara_ai.workflow.core.workflow import WorkflowRegistry

from ...auth.middleware import require_auth
from .models import SystemStatus, SystemStatusResponse, UpdateCheckResponse

system_bp = Blueprint("system", __name__)

# 记录启动时间
start_time = time.time()

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

def get_version() -> str:
    """获取当前安装的版本号"""
    try:
        # 使用 importlib.metadata 获取已安装的包版本
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("kirara-ai")
        except PackageNotFoundError:
            # 如果包未安装，尝试从 pkg_resources 获取
            from pkg_resources import get_distribution
            return get_distribution("kirara-ai").version
    except Exception:
        return "0.0.0"  # 如果所有方法都失败，返回默认版本号


async def get_latest_pypi_version(package_name: str, registry: str = "https://pypi.org/simple") -> tuple[str, str]:
    """获取包的最新版本和下载URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{registry}/{package_name}/json") as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["info"]["version"]
                # 获取最新版本的wheel包下载URL
                for url_info in data["urls"]:
                    if url_info["packagetype"] == "bdist_wheel":
                        return latest_version, url_info["url"]
        return latest_version, ""
    except Exception:
        return "0.0.0", ""


async def get_latest_npm_version(package_name: str, registry: str = "https://registry.npmjs.org") -> tuple[str, str]:
    """获取NPM包的最新版本和下载URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{registry}/{package_name}") as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["dist-tags"]["latest"]
                tarball_url = data["versions"][latest_version]["dist"]["tarball"]
        return latest_version, tarball_url
    except Exception:
        return "0.0.0", ""


async def download_file(url: str, temp_dir: str) -> tuple[str, str]:
    """下载文件并返回文件路径和SHA256"""
    local_filename = os.path.join(temp_dir, url.split('/')[-1])
    sha256_hash = hashlib.sha256()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('Content-Length', 0))
                bytes_downloaded = 0

                with open(local_filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        bytes_downloaded += len(chunk)
                        if total_size > 0:
                            print(f"Downloaded {bytes_downloaded / total_size:.2%}", end='\r')
                print()  # 换行，确保进度条不覆盖后续输出
        return local_filename, sha256_hash.hexdigest()
    except Exception as e:
        print(f"下载失败: {e}")
        return "", ""


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
    process = psutil.Process()
    memory_usage = {
        "rss": process.memory_info().rss / 1024 / 1024,  # MB
        "vms": process.memory_info().vms / 1024 / 1024,  # MB
        "percent": process.memory_percent(),
    }
    cpu_usage = process.cpu_percent()

    status = SystemStatus(
        uptime=uptime,
        active_adapters=active_adapters,
        active_backends=active_backends,
        loaded_plugins=loaded_plugins,
        workflow_count=workflow_count,
        memory_usage=memory_usage,
        cpu_usage=cpu_usage,
        version=get_version(),
    )

    return SystemStatusResponse(status=status).model_dump()


@system_bp.route("/check-update", methods=["GET"])
@require_auth
async def check_update():
    """检查系统更新"""
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    pypi_registry = config.update.pypi_registry
    npm_registry = config.update.npm_registry
    
    current_backend_version = get_version()
    latest_backend_version, backend_download_url = await get_latest_pypi_version("kirara-ai", pypi_registry)
    
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
            subprocess.run([sys.executable, "-m", "pip", "install", backend_file], check=True)
        
        if update_webui:
            webui_url = data["webui_download_url"]
            webui_file, webui_hash = await download_file(webui_url, temp_dir)
            # 解压并安装前端
            static_dir = current_app.static_folder
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
    raise SystemExit("restart")