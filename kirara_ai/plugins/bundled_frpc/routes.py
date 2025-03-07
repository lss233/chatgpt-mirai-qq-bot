import asyncio

from quart import Blueprint, Response, g, request

from kirara_ai.config.config_loader import CONFIG_FILE, ConfigLoader
from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.web.auth.middleware import require_auth

from .frpc_manager import FrpcManager
from .models import FrpcConfigUpdate, FrpcDownloadProgress, FrpcStatus

frpc_bp = Blueprint("frpc", __name__)


@frpc_bp.route("/status", methods=["GET"])
@require_auth
async def get_status():
    """获取 FRPC 状态"""
    frpc_manager: FrpcManager = g.frpc_manager
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    is_running, version, remote_url, error_message, download_progress = frpc_manager.get_status()
    is_installed = frpc_manager.is_installed()
    
    return FrpcStatus(
        is_running=is_running,
        is_installed=is_installed,
        config=config.frpc,
        version=version,
        remote_url=remote_url,
        error_message=error_message,
        download_progress=download_progress
    ).model_dump()


@frpc_bp.route("/config", methods=["POST"])
@require_auth
async def update_config():
    """更新 FRPC 配置"""
    frpc_manager: FrpcManager = g.frpc_manager
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    data = await request.get_json()
    config_update = FrpcConfigUpdate(**data)
    
    # 更新配置
    frpc_config = config.frpc
    
    # 使用字典推导式更新非 None 字段
    update_dict = {k: v for k, v in config_update.model_dump().items() if v is not None}
    
    # 更新配置
    for key, value in update_dict.items():
        setattr(frpc_config, key, value)
    
    # 保存配置
    ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
    
    # 如果启用状态改变，启动或停止 frpc
    web_port = config.web.port
    if config_update.enable is not None:
        if config_update.enable:
            frpc_manager.start_frpc(web_port)
        else:
            frpc_manager.stop_frpc()
    # 如果其他配置改变且 frpc 正在运行，重启 frpc
    elif frpc_config.enable and any(k != "enable" for k in update_dict.keys()):
        frpc_manager.stop_frpc()
        frpc_manager.start_frpc(web_port)
    
    # 返回最新状态
    is_running, version, remote_url, error_message, download_progress = frpc_manager.get_status()
    is_installed = frpc_manager.is_installed()
    
    return FrpcStatus(
        is_running=is_running,
        is_installed=is_installed,
        config=config.frpc,
        version=version,
        remote_url=remote_url,
        error_message=error_message,
        download_progress=download_progress
    ).model_dump()


@frpc_bp.route("/start", methods=["POST"])
@require_auth
async def start_frpc():
    """启动 FRPC"""
    frpc_manager: FrpcManager = g.frpc_manager
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    # 更新配置中的启用状态
    config.frpc.enable = True
    
    # 保存配置
    ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
    
    # 启动 frpc
    success = frpc_manager.start_frpc(config.web.port)
    
    # 返回最新状态
    is_running, version, remote_url, error_message, download_progress = frpc_manager.get_status()
    is_installed = frpc_manager.is_installed()
    
    return FrpcStatus(
        is_running=is_running,
        is_installed=is_installed,
        config=config.frpc,
        version=version,
        remote_url=remote_url,
        error_message=error_message,
        download_progress=download_progress
    ).model_dump()


@frpc_bp.route("/stop", methods=["POST"])
@require_auth
async def stop_frpc():
    """停止 FRPC"""
    frpc_manager: FrpcManager = g.frpc_manager
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    
    # 更新配置中的启用状态
    config.frpc.enable = False
    
    # 保存配置
    ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
    
    # 停止 frpc
    success = frpc_manager.stop_frpc()
    
    # 返回最新状态
    is_running, version, remote_url, error_message, download_progress = frpc_manager.get_status()
    is_installed = frpc_manager.is_installed()
    
    return FrpcStatus(
        is_running=is_running,
        is_installed=is_installed,
        config=config.frpc,
        version=version,
        remote_url=remote_url,
        error_message=error_message,
        download_progress=download_progress
    ).model_dump()

@frpc_bp.route("/download", methods=["GET"])
@require_auth
async def download_frpc():
    """下载 FRPC 并通过 SSE 返回进度"""
    frpc_manager: FrpcManager = g.frpc_manager
    
    # 创建一个队列用于存储SSE事件
    queue = asyncio.Queue()
    
    # 定义进度回调函数
    async def progress_callback(progress: float):
        """进度回调函数"""
        status = "downloading"
        if progress >= 100:
            status = "completed"
        
        # 将事件放入队列
        await queue.put(
            FrpcDownloadProgress(
                progress=progress, 
                status=status
            ).model_dump_json()
        )
    
    # 启动下载任务
    async def download_task():
        try:
            # 发送初始状态
            await queue.put(
                FrpcDownloadProgress(
                    progress=0, 
                    status='downloading'
                ).model_dump_json()
            )
            
            # 执行下载
            success = await frpc_manager.download_frpc(progress_callback)
            
            # 如果下载失败，发送错误状态
            if not success:
                await queue.put(
                    FrpcDownloadProgress(
                        progress=0, 
                        status='error', 
                        error_message=frpc_manager._error_message
                    ).model_dump_json()
                )
        except Exception as e:
            # 发送错误状态
            await queue.put(
                FrpcDownloadProgress(
                    progress=0, 
                    status='error', 
                    error_message=str(e)
                ).model_dump_json()
            )
        finally:
            # 标记队列结束
            await queue.put(None)
    
    # 启动下载任务
    asyncio.create_task(download_task())
    
    # 定义SSE流生成器
    async def send_events():
        while True:
            message = await queue.get()
            if message is None:  # 结束信号
                break
            yield f"data: {message}\n\n"
    
    # 返回SSE响应
    return Response(
        send_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Connection": "keep-alive"
        }
    ) 