from quart import g

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.web.app import WebServer

from .frpc_manager import FrpcManager
from .routes import frpc_bp

logger = get_logger("FRPC")


class FrpcPlugin(Plugin):
    """
    FRPC 插件
    
    用于在本地启动 FRPC 服务，协助将 Web 服务暴露到外网。
    """
    web_server: WebServer
    global_config: GlobalConfig
    
    def __init__(self):
        self.frpc_manager = None
    
    def on_load(self):
        # 创建 FRPC 管理器
        self.frpc_manager = FrpcManager(self.global_config)
        
        # 注册中间件，将 frpc_manager 注入到请求上下文
        @frpc_bp.before_request
        async def inject_frpc_manager():
            g.frpc_manager = self.frpc_manager
    
    def on_start(self):
        # 挂载 API
        self.web_server.web_api_app.register_blueprint(frpc_bp, url_prefix="/api/frpc")
        
        # 如果配置为启用，则尝试启动 frpc
        if self.global_config.frpc.enable:
            try:
                self.frpc_manager.start_frpc(self.global_config.web.port)
            except Exception as e:
                logger.error(f"启动 FRPC 失败: {e}")
    
    def on_stop(self):
        # 停止 frpc 进程
        if self.frpc_manager:
            self.frpc_manager.stop_frpc()


__all__ = ["FrpcPlugin"] 