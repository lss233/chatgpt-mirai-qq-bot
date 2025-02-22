import time
from pathlib import Path

import psutil
import tomli
from quart import Blueprint, g

from kirara_ai.im.manager import IMManager
from kirara_ai.llm.llm_manager import LLMManager
from kirara_ai.plugin_manager.plugin_loader import PluginLoader
from kirara_ai.workflow.core.workflow import WorkflowRegistry

from ...auth.middleware import require_auth
from .models import SystemStatus, SystemStatusResponse

system_bp = Blueprint("system", __name__)

# 记录启动时间
start_time = time.time()


def get_version() -> str:
    """从 pyproject.toml 读取版本号"""
    try:
        pyproject_path = (
            Path(__file__).parent.parent.parent.parent.parent / "pyproject.toml"
        )
        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)
            return pyproject["project"]["version"]
    except Exception:
        return "0.0.0"  # 如果读取失败，返回默认版本号


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
