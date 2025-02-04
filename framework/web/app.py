import asyncio
from quart import Quart, g
from framework.config.global_config import GlobalConfig
from quart_cors import cors
from hypercorn.config import Config
from hypercorn.asyncio import serve

from framework.config import get_config
from framework.logger import get_async_logger
from framework.ioc.container import DependencyContainer
from .auth.routes import auth_bp
from .api.im import im_bp
from .api.llm import llm_bp
from .api.dispatch import dispatch_bp
from .api.block import block_bp
from .api.workflow import workflow_bp

def create_app(container: DependencyContainer) -> Quart:
    app = Quart(__name__)
    app = cors(app)  # 启用CORS支持
    
    # 配置
    config = container.resolve(GlobalConfig)
    app.config['SECRET_KEY'] = config.web.secret_key
    
    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(im_bp, url_prefix='/api/im')
    app.register_blueprint(llm_bp, url_prefix='/api/llm')
    app.register_blueprint(dispatch_bp, url_prefix='/api/dispatch')
    app.register_blueprint(block_bp, url_prefix='/api/block')
    app.register_blueprint(workflow_bp, url_prefix='/api/workflow')
    
    # 在每个请求前将容器注入到上下文
    @app.before_request
    async def inject_container():
        g.container = container
    
    return app

class WebServer:
    def __init__(self, container: DependencyContainer):
        self.app = create_app(container)
        self.config = container.resolve(GlobalConfig)
        self.logger = get_async_logger("WebServer")
        
        # 配置 hypercorn
        self.hypercorn_config = Config()
        self.hypercorn_config.bind = [f"{self.config.web.host}:{self.config.web.port}"]
        self.hypercorn_config._log = self.logger
    
    async def start(self):
        """启动Web服务器"""
        self.server_task = asyncio.create_task(
            serve(self.app, self.hypercorn_config)
        )
    
    async def stop(self):
        """停止Web服务器"""
        if hasattr(self, 'server_task'):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error during server shutdown: {e}")

# 全局Web服务器实例
web_server = WebServer() 