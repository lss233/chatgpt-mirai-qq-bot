import asyncio
from pathlib import Path

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, g
from quart_cors import cors
from werkzeug.exceptions import NotFound

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.logger import HypercornLoggerWrapper, get_logger
from kirara_ai.web.auth.services import AuthService, FileBasedAuthService

from .api.block import block_bp
from .api.dispatch import dispatch_bp
from .api.im import im_bp
from .api.llm import llm_bp
from .api.plugin import plugin_bp
from .api.system import system_bp
from .api.workflow import workflow_bp
from .auth.routes import auth_bp

ERROR_MESSAGE = """
<h1>WebUI launch failed!</h1>
<p lang="en">Web UI not found. Please download from <a href='https://github.com/DarkSkyTeam/chatgpt-for-bot-webui/releases' target='_blank'>here</a> and extract to the <span>web</span> folder, make sure the <span>web/index.html</span> file exists.</p>
<h1>WebUI 启动失败！</h1>
<p lang="zh-CN">Web UI 未找到。请从 <a href='https://github.com/DarkSkyTeam/chatgpt-for-bot-webui/releases' target='_blank'>这里</a> 下载并解压到 <span>web</span> 文件夹，确保 <span>web/index.html</span> 文件存在。</p>

<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f0f0f0;
        color: #333;
        padding: 20px;
    }
    h1 {
        color: #333;
        font-size: 24px;
        margin-bottom: 10px;
    }
    p {
        font-size: 16px;
        margin-bottom: 10px;
    }
    a {
        color: #007bff;
        text-decoration: none;
    }
</style>
"""


def create_app(container: DependencyContainer) -> Quart:
    app = Quart(__name__)
    app.static_folder = "../../web"

    @app.route("/")
    async def index():
        try:
            return await app.send_static_file("index.html")
        except Exception as e:
            return ERROR_MESSAGE

    @app.route("/<path:path>")
    async def serve_static(path):
        if path.startswith("backend-api"):
            raise NotFound()
        try:
            return await app.send_static_file(path)
        except Exception as e:
            return await app.send_static_file("index.html")

    app = cors(app)  # 启用CORS支持
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600
    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix="/backend-api/api/auth")
    app.register_blueprint(im_bp, url_prefix="/backend-api/api/im")
    app.register_blueprint(llm_bp, url_prefix="/backend-api/api/llm")
    app.register_blueprint(dispatch_bp, url_prefix="/backend-api/api/dispatch")
    app.register_blueprint(block_bp, url_prefix="/backend-api/api/block")
    app.register_blueprint(workflow_bp, url_prefix="/backend-api/api/workflow")
    app.register_blueprint(plugin_bp, url_prefix="/backend-api/api/plugin")
    app.register_blueprint(system_bp, url_prefix="/backend-api/api/system")

    # 在每个请求前将容器注入到上下文
    @app.before_request
    async def inject_container():
        g.container = container

    app.container = container

    return app


class WebServer:
    def __init__(self, container: DependencyContainer):
        self.app = create_app(container)
        container.register(
            AuthService,
            FileBasedAuthService(
                password_file=Path(container.resolve(GlobalConfig).web.password_file),
                secret_key=container.resolve(GlobalConfig).web.secret_key,
            ),
        )
        self.config = container.resolve(GlobalConfig)
        self.logger = get_logger("WebServer")

        # 配置 hypercorn
        from hypercorn.logging import Logger

        self.hypercorn_config = Config()
        self.hypercorn_config.bind = [f"{self.config.web.host}:{self.config.web.port}"]
        self.hypercorn_config._log = Logger(self.hypercorn_config)
        # 这些是 logging.Logger，需要转换成 loguru.Logger 的格式
        self.hypercorn_config._log.access_logger = HypercornLoggerWrapper(self.logger)
        self.hypercorn_config._log.error_logger = HypercornLoggerWrapper(self.logger)

    async def start(self):
        """启动Web服务器"""
        self.server_task = asyncio.create_task(serve(self.app, self.hypercorn_config))
        self.logger.info(
            f"监听地址：http://{self.config.web.host}:{self.config.web.port}/"
        )

    async def stop(self):
        """停止Web服务器"""
        if hasattr(self, "server_task"):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error during server shutdown: {e}")
