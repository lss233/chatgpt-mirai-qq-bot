import io
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Awaitable, Callable, Optional, Tuple

import aiohttp

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.logger import get_logger

logger = get_logger("FRPC")

# 存储路径
STORAGE_PATH = "./data/frpc"


class FrpcManager:
    """FRPC 管理器"""
    
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config
        self._frpc_process: Optional[subprocess.Popen] = None
        self._frpc_version: str = ""
        self._remote_url: str = ""
        self._error_message: str = ""
        self._download_progress: float = 0
        
        # 确保存储目录存在
        self.storage_path = Path(STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 设置 frpc 可执行文件路径
        system = platform.system().lower()
        if system == "windows":
            self._frpc_path = self.storage_path / "frpc.exe"
        else:
            self._frpc_path = self.storage_path / "frpc"
        
        # 设置配置文件路径
        self._frpc_config_path = self.storage_path / "frpc.ini"
        
        # 尝试获取版本信息
        if self.is_installed():
            self._get_frpc_version()
    
    async def download_frpc(self, progress_callback: Optional[Callable[[float], Awaitable[None]]] = None) -> bool:
        """下载 FRPC"""
        # 重置状态
        self._download_progress = 0
        self._error_message = ""
        
        try:
            # 获取系统信息
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            # 确定下载 URL
            if system == "windows":
                if machine in ["amd64", "x86_64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_windows_amd64.zip"
                elif machine in ["arm64", "aarch64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_windows_arm64.zip"
                else:
                    self._error_message = f"不支持的系统架构: {machine}"
                    if progress_callback:
                        await progress_callback(0)
                    return False
            elif system == "linux":
                if machine in ["amd64", "x86_64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_linux_amd64.tar.gz"
                elif machine in ["arm64", "aarch64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_linux_arm64.tar.gz"
                elif machine.startswith("arm"):
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_linux_arm.tar.gz"
                else:
                    self._error_message = f"不支持的系统架构: {machine}"
                    if progress_callback:
                        await progress_callback(0)
                    return False
            elif system == "darwin":
                if machine in ["amd64", "x86_64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_darwin_amd64.tar.gz"
                elif machine in ["arm64", "aarch64"]:
                    url = "https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_darwin_arm64.tar.gz"
                else:
                    self._error_message = f"不支持的系统架构: {machine}"
                    if progress_callback:
                        await progress_callback(0)
                    return False
            else:
                self._error_message = f"不支持的操作系统: {system}"
                if progress_callback:
                    await progress_callback(0)
                return False
            
            self._remote_url = url
            self._version = "v0.51.3"
            
            # 下载文件
            try:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            self._error_message = f"下载失败: HTTP {response.status}"
                            if progress_callback:
                                await progress_callback(0)
                            return False
                        
                        total_size = int(response.headers.get("content-length", 0))
                        downloaded_size = 0
                        
                        # 直接在内存中下载文件
                        content = bytearray()
                        async for chunk in response.content.iter_chunked(8192):
                            content.extend(chunk)
                            downloaded_size += len(chunk)
                            progress = min(100, downloaded_size * 100 / total_size if total_size > 0 else 0)
                            self._download_progress = progress
                            if progress_callback:
                                await progress_callback(progress)
                
                # 解压文件
                extract_dir = tempfile.mkdtemp()
                try:
                    # 从内存中解压文件
                    if url.endswith(".zip"):
                        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
                            zip_ref.extractall(extract_dir)
                    elif url.endswith(".tar.gz"):
                        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar_ref:
                            tar_ref.extractall(extract_dir)
                    
                    # 查找 frpc 可执行文件
                    frpc_name = "frpc.exe" if system == "windows" else "frpc"
                    frpc_files = []
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if file == frpc_name:
                                frpc_files.append(os.path.join(root, file))
                    
                    if not frpc_files:
                        self._error_message = "解压后未找到 frpc 可执行文件"
                        if progress_callback:
                            await progress_callback(0)
                        return False
                    
                    # 复制 frpc 可执行文件
                    frpc_path = str(self._frpc_path)
                    shutil.copy2(frpc_files[0], frpc_path)
                    
                    # 设置可执行权限
                    if system != "windows":
                        os.chmod(frpc_path, 0o755)
                    
                    self._frpc_path = frpc_path
                    if progress_callback:
                        await progress_callback(100)
                    return True
                finally:
                    shutil.rmtree(extract_dir)
            except Exception as e:
                self._error_message = f"下载失败: {str(e)}"
                if progress_callback:
                    await progress_callback(0)
                return False
        except Exception as e:
            self._error_message = f"下载失败: {str(e)}"
            if progress_callback:
                await progress_callback(0)
            return False
    
    def _get_frpc_version(self):
        """获取 frpc 版本信息"""
        try:
            if not self.is_installed():
                self._frpc_version = "未安装"
                return
            
            result = subprocess.run(
                [str(self._frpc_path), "-v"],
                capture_output=True,
                text=True,
                check=True
            )
            self._frpc_version = result.stdout.strip()
            logger.info(f"FRPC 版本: {self._frpc_version}")
        except Exception as e:
            logger.error(f"获取 FRPC 版本失败: {e}")
            self._frpc_version = "未知"
    
    def _generate_config(self, web_port: int) -> bool:
        """
        生成 frpc 配置文件
        
        Args:
            web_port: Web 服务端口
            
        Returns:
            bool: 配置文件生成是否成功
        """
        try:
            config = self.global_config.frpc
            
            # 基本配置
            config_content = f"""[common]
server_addr = {config.server_addr}
server_port = {config.server_port}
"""
            
            # 如果有令牌，添加令牌配置
            if config.token:
                config_content += f"token = {config.token}\n"
            
            if self.global_config.web.host == "0.0.0.0":
                web_ip = "127.0.0.1"
            else:
                web_ip = self.global_config.web.host
            # 代理配置
            config_content += f"""
[kirara_web]
type = tcp
local_ip = {web_ip}
local_port = {web_port}
"""
            
            # 远程端口配置
            if config.remote_port > 0:
                config_content += f"remote_port = {config.remote_port}\n"
            
            # 写入配置文件
            with open(self._frpc_config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            
            logger.info(f"FRPC 配置文件已生成: {self._frpc_config_path}")
            return True
        
        except Exception as e:
            logger.error(f"生成 FRPC 配置文件失败: {e}")
            self._error_message = f"生成 FRPC 配置文件失败: {e}"
            return False
    
    def start_frpc(self, web_port: int) -> bool:
        """
        启动 frpc
        
        Args:
            web_port: Web 服务端口
            
        Returns:
            bool: 启动是否成功
        """
        if self.is_installed():
            self._get_frpc_version()
        try:
            # 如果已经在运行，先停止
            if self._frpc_process is not None:
                self.stop_frpc()
            
            # 检查可执行文件是否存在
            if not self.is_installed():
                logger.error("FRPC 可执行文件不存在，请先下载")
                self._error_message = "FRPC 可执行文件不存在，请先下载"
                return False
            
            # 生成配置文件
            if not self._generate_config(web_port):
                return False
            
            # 启动 frpc
            cmd = [str(self._frpc_path), "-c", str(self._frpc_config_path)]
            self._frpc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            def print_output(process):
                while process.poll() is None:
                    line = process.stdout.readline()
                    if not line:
                        break
                    logger.info(line.strip())
                logger.info("FRPC 已结束")

            # 创建一个线程来读取和打印输出
            output_thread = threading.Thread(target=print_output, args=(self._frpc_process,))
            output_thread.daemon = True  # 设置为守护线程，主线程退出时自动结束
            output_thread.start()
                        
            logger.info(f"FRPC 已启动，PID: {self._frpc_process.pid}")
            
            # 计算远程访问 URL
            self._calculate_remote_url()
            
            return True
        
        except Exception as e:
            logger.error(f"启动 FRPC 失败: {e}")
            self._error_message = f"启动 FRPC 失败: {e}"
            return False
    
    def stop_frpc(self) -> bool:
        """
        停止 frpc
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if self._frpc_process is not None:
                self._frpc_process.terminate()
                try:
                    self._frpc_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._frpc_process.kill()
                
                logger.info("FRPC 已停止")
                self._frpc_process = None
                self._remote_url = ""
            
            return True
        
        except Exception as e:
            logger.error(f"停止 FRPC 失败: {e}")
            self._error_message = f"停止 FRPC 失败: {e}"
            return False
    
    def _calculate_remote_url(self):
        """计算远程访问 URL"""
        config = self.global_config.frpc
        
        if config.remote_port > 0:
            self._remote_url = f"http://{config.server_addr}:{config.remote_port}"
        else:
            self._remote_url = f"http://{config.server_addr}:随机端口"
    
    def get_status(self) -> Tuple[bool, str, str, str, float]:
        """
        获取 frpc 状态
        
        Returns:
            Tuple[bool, str, str, str, float]: (是否运行, 版本, 远程URL, 错误信息, 下载进度)
        """
        is_running = self._frpc_process is not None and self._frpc_process.poll() is None
        
        # 如果进程已经退出，获取错误信息
        if self._frpc_process is not None and self._frpc_process.poll() is not None:
            stderr = self._frpc_process.stderr.read() if self._frpc_process.stderr else ""
            if stderr:
                self._error_message = stderr
            self._frpc_process = None
        
        return (
            is_running,
            self._frpc_version,
            self._remote_url,
            self._error_message,
            self._download_progress
        )
    
    def is_installed(self) -> bool:
        """
        检查 frpc 是否已安装
        
        Returns:
            bool: 是否已安装
        """
        return os.path.exists(self._frpc_path) 