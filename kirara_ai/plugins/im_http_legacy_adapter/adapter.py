import asyncio
import json
import re
import time
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field
from quart import Quart, request

from kirara_ai.im.adapter import IMAdapter
from kirara_ai.im.message import ImageMessage, IMMessage, TextMessage, VoiceMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.workflow.core.dispatch import WorkflowDispatcher


class HttpLegacyConfig(BaseModel):
    """HTTP Legacy API 配置"""

    host: str = Field(default="127.0.0.1", description="HTTP服务器监听地址")
    port: int = Field(default=8080, description="HTTP服务器监听端口")
    debug: bool = Field(default=False, description="是否开启调试模式")
    model_config = ConfigDict(extra="allow")


class ResponseResult:
    def __init__(self, message=None, voice=None, image=None, result_status="SUCCESS"):
        self.result_status = result_status
        self.message = (
            []
            if message is None
            else message if isinstance(message, list) else [message]
        )
        self.voice = (
            [] if voice is None else voice if isinstance(voice, list) else [voice]
        )
        self.image = (
            [] if image is None else image if isinstance(image, list) else [image]
        )

    def to_json(self):
        return json.dumps(
            {
                "result": self.result_status,
                "message": self.message,
                "voice": self.voice,
                "image": self.image,
            }
        )

    def pop_all(self):
        self.message = []
        self.voice = []
        self.image = []


class MessageHandler(Protocol):
    async def __call__(self, message: IMMessage) -> None: ...


class V2Request:
    def __init__(self, session_id: str, username: str, message: str, request_time: str):
        self.session_id = session_id
        self.username = username
        self.message = message
        self.result = ResponseResult()
        self.request_time = request_time
        self.done = False
        self.response_event = asyncio.Event()


class HttpLegacyAdapter(IMAdapter):
    """HTTP Legacy API适配器"""

    dispatcher: WorkflowDispatcher

    def __init__(self, config: HttpLegacyConfig):
        self.config = config
        self.app = Quart(__name__)
        self.request_dic = {}
        self.setup_routes()

    def convert_to_message(self, raw_message: Any) -> IMMessage:
        data = raw_message
        username = data.get("username", "某人")
        message_text = data.get("message", "")
        session_id = data.get("session_id", "friend-default_session")

        if (
            session_id.startswith("group-")
            and len(session_id.split("-")) == 2
            and ":" in session_id.split("-")[1]
        ):
            # group-group_id:user_id
            ids = session_id.split("-")[1].split(":")
            sender = ChatSender.from_group_chat(
                user_id=ids[1], group_id=ids[0], display_name=username
            )
        else:
            sender = ChatSender.from_c2c_chat(user_id=session_id, display_name=username)

        return IMMessage(
            sender=sender,
            message_elements=[TextMessage(text=message_text)],
            raw_message={"session_id": session_id, **data},
        )

    async def handle_message_elements(self, result: ResponseResult, message: IMMessage):
        for element in message.message_elements:
            if isinstance(element, TextMessage):
                result.message.append(element.text)
            elif isinstance(element, VoiceMessage):
                result.voice.append(element.url)
            elif isinstance(element, ImageMessage):
                result.image.append(element.url)

    def setup_routes(self):
        @self.app.route("/v1/chat", methods=["POST"])
        async def v1_chat():
            data = await request.get_json()
            result = ResponseResult()

            async def handle_response(resp_message: IMMessage):
                await self.handle_message_elements(result, resp_message)

            message = self.convert_to_message(data)
            message.sender.callback = handle_response

            await self.dispatcher.dispatch(self, message)
            return result.to_json()

        @self.app.route("/v2/chat", methods=["POST"])
        async def v2_chat():
            data = await request.get_json()
            request_time = str(int(time.time() * 1000))

            message = self.convert_to_message(data)
            session_id = message.raw_message["session_id"]

            bot_request = V2Request(
                session_id,
                message.sender.display_name,
                data.get("message", ""),
                request_time,
            )
            self.request_dic[request_time] = bot_request

            async def handle_response(resp_message: IMMessage):
                await self.handle_message_elements(bot_request.result, resp_message)
                bot_request.response_event.set()

            message.sender.callback = handle_response
            asyncio.create_task(self.dispatcher.dispatch(self, message))
            return request_time

        @self.app.route("/v2/chat/response", methods=["GET"])
        async def v2_chat_response():
            request_id = request.args.get("request_id", "")
            request_id = re.sub(r'^[%22%27"\'"]*|[%22%27"\'"]*$', "", request_id)

            bot_request = self.request_dic.get(request_id)
            if bot_request is None:
                return ResponseResult(
                    message="没有更多了！", result_status="FAILED"
                ).to_json()

            await bot_request.response_event.wait()
            bot_request.response_event.clear()

            response = bot_request.result.to_json()
            bot_request.result = ResponseResult()

            if bot_request.done:
                self.request_dic.pop(request_id)

            return response

    async def send_message(self, message: IMMessage, recipient: Any):
        """此处负责 HTTP 的响应逻辑"""
        if isinstance(recipient, ChatSender):
            await recipient.callback(message)

    async def start(self):
        """启动HTTP服务器"""
        # 使用 hypercorn 配置来正确处理关闭信号
        from hypercorn.config import Config
        from hypercorn.logging import Logger

        from kirara_ai.logger import HypercornLoggerWrapper

        config = Config()
        config.bind = [f"{self.config.host}:{self.config.port}"]
        config._log = Logger(config)
        config._log.access_logger = HypercornLoggerWrapper(self.app.logger)
        config._log.error_logger = HypercornLoggerWrapper(self.app.logger)
        from hypercorn.asyncio import serve

        self.server_task = asyncio.create_task(serve(self.app, config))

        # 启动清理过期请求的任务
        self.cleanup_task = asyncio.create_task(self.cleanup_expired_requests())

    async def cleanup_expired_requests(self):
        """清理过期的请求"""
        while True:
            now = time.time()
            expired_keys = [
                key
                for key, req in self.request_dic.items()
                if now - int(key) / 1000 > 600
            ]
            for key in expired_keys:
                self.request_dic.pop(key)
            await asyncio.sleep(60)

    async def stop(self):
        """停止HTTP服务器"""
        if hasattr(self, "server_task"):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.app.logger.error(f"Error during server shutdown: {e}")

        if hasattr(self, "cleanup_task"):
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
