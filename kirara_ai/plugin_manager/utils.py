import importlib.util
import shutil
import sys
from importlib.metadata import PackageNotFoundError, distribution
from typing import Any, Dict, Optional


def build_package_manager_command(action: str, *args: str) -> list[str]:
    """Build a uv/pip command targeting the current Python environment."""
    if uv := shutil.which("uv"):
        return [uv, "pip", action, "--python", sys.executable, *args]
    if importlib.util.find_spec("pip") is not None:
        assume_yes = ["-y"] if action == "uninstall" else []
        return [sys.executable, "-m", "pip", action, *assume_yes, *args]
    raise RuntimeError("Plugin management requires uv or pip")


def get_package_metadata(package_name: str) -> Optional[Dict[str, Any]]:
    """获取Python包的元数据

    Args:
        package_name: 包名

    Returns:
        包含包元数据的字典，如果包不存在则返回None
    """
    try:
        dist = distribution(package_name)
        return {
            "name": dist.metadata["Name"],
            "version": dist.version,
            "description": dist.metadata["Summary"] if "Summary" in dist.metadata else "",
            "author": dist.metadata["Author"] if "Author" in dist.metadata else "",
        }
    except PackageNotFoundError:
        return None
