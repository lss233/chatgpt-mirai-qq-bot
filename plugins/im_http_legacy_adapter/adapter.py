import asyncio
from typing import Any
import json
from quart import Quart, request
from pydantic import BaseModel, Field
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage, TextMessage, VoiceMessage, ImageMessage
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher

class HttpLegacyConfig(BaseModel):
    """HTTP Legacy API 配置"""
    host: str = Field(default="127.0.0.1", description="HTTP服务器监听地址")
    port: int = Field(default=8080, description="HTTP服务器监听端口")
    debug: bool = Field(default=False, description="是否开启调试模式")

    class Config:
        extra = "allow"

# 封装sender信息
class Sender:
    def __init__(self, username, callback):
        self.username = username
        self.callback = callback

    async def __call__(self, message):
        await self.callback(message)
        
class ResponseResult:
    def __init__(self, message=None, voice=None, image=None, result_status="SUCCESS"):
        self.result_status = result_status
        self.message = [] if message is None else message if isinstance(message, list) else [message]
        self.voice = [] if voice is None else voice if isinstance(voice, list) else [voice]
        self.image = [] if image is None else image if isinstance(image, list) else [image]

    def to_json(self):
        return json.dumps({
            'result': self.result_status,
            'message': self.message,
            'voice': self.voice,
            'image': self.image
        })

class HttpLegacyAdapter(IMAdapter):
    """HTTP Legacy API适配器"""
    dispatcher: WorkflowDispatcher
    def __init__(self, config: HttpLegacyConfig):
        self.config = config
        self.app = Quart(__name__)
        self.setup_routes()
    def convert_to_message(self, raw_message: Any) -> IMMessage:
        data = raw_message
        username = data.get('username', '某人')
        message_text = data.get('message', '')
        
        # 构造IMMessage
        return IMMessage(
            sender=Sender(username, None), # handle_response will be set later
            message_elements=[TextMessage(text=message_text)],
            raw_message=data
        )
    
    def setup_routes(self):
        @self.app.route('/v1/chat', methods=['POST'])
        async def chat():
            data = await request.get_json()
            
            # 创建响应结果
            result = ResponseResult()

            # 处理消息并获取响应
            async def handle_response(resp_message: IMMessage):
                for element in resp_message.message_elements:
                    if isinstance(element, TextMessage):
                        result.message.append(element.text)
                    elif isinstance(element, VoiceMessage):
                        result.voice.append(element.url)
                    elif isinstance(element, ImageMessage):
                        result.image.append(element.url)

            # 转换消息并设置回调
            message = self.convert_to_message(data)
            message.sender.callback = handle_response
            
            await self.dispatcher.dispatch(self, message)
            return result.to_json()

    async def send_message(self, message: IMMessage, recipient: Any):
        """此处负责 HTTP 的响应逻辑"""
        if isinstance(recipient, Sender):
            await recipient(message)

    async def start(self):
        """启动HTTP服务器"""
        from framework.logger import get_logger
        self.app.logger = get_logger("HTTP-Legacy-Adapter")
        
        # 使用 hypercorn 配置来正确处理关闭信号
        from hypercorn.config import Config
        config = Config()
        config.bind = [f"{self.config.host}:{self.config.port}"]
        
        from hypercorn.asyncio import serve
        self.server_task = asyncio.create_task(
            serve(self.app, config)
        )

    async def stop(self):
        """停止HTTP服务器"""
        if hasattr(self, 'server_task'):
            # 优雅地关闭服务器
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass  # 预期的取消异常，可以忽略
            except Exception as e:
                self.app.logger.error(f"Error during server shutdown: {e}")
