import json
from typing import Any
from wechatpy.work.crypto import WeChatCrypto
from wechatpy.work.client import WeChatClient
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.work.exceptions import InvalidCorpIdException
from wechatpy.work import parse_message, create_reply
from quart import Quart, request, abort
from pydantic import BaseModel, Field
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage, TextMessage, VoiceMessage, ImageMessage
from framework.logger import get_logger
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher
import asyncio
import base64
from io import BytesIO

class WecomConfig(BaseModel):
    """企业微信配置
    文档： https://work.weixin.qq.com/api/doc/90000/90136/91770
    """

    corp_id: str = Field(description="企业ID")
    agent_id: int = Field(description="应用ID") 
    secret: str = Field(description="应用Secret")
    token: str = Field(description="Token")
    encoding_aes_key: str = Field(description="EncodingAESKey")
    host: str = Field(default="127.0.0.1", description="HTTP服务器监听地址")
    port: int = Field(default=8080, description="HTTP服务器监听端口")
    debug: bool = Field(default=False, description="是否开启调试模式")

    class Config:
        extra = "allow"

class WecomAdapter(IMAdapter):
    """企业微信适配器"""
    dispatcher: WorkflowDispatcher

    def __init__(self, config: WecomConfig):
        self.config = config
        self.app = Quart(__name__)
        self.crypto = WeChatCrypto(config.token, config.encoding_aes_key, config.corp_id)
        self.client = WeChatClient(config.corp_id, config.secret)
        self.logger = get_logger("Wecom-Adapter")
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/wechat", methods=["GET", "POST"])
        async def wechat():
            signature = request.args.get("msg_signature", "")
            timestamp = request.args.get("timestamp", "")
            nonce = request.args.get("nonce", "")

            if request.method == "GET":
                echo_str = request.args.get("echostr", "")
                try:
                    echo_str = self.crypto.check_signature(signature, timestamp, nonce, echo_str)
                except InvalidSignatureException:
                    abort(403)
                return echo_str
            else:
                try:
                    msg = self.crypto.decrypt_message(await request.data, signature, timestamp, nonce)
                except (InvalidSignatureException, InvalidCorpIdException):
                    abort(403)
                msg = parse_message(msg)
                if msg.type == "text":
                    # 构造消息对象
                    message = self.convert_to_message(msg)
                    # 分发消息
                    await self.dispatcher.dispatch(self, message)
                    return "ok"
                else:
                    reply = create_reply("暂不支持该类型消息", msg).render()
                    return self.crypto.encrypt_message(reply, nonce, timestamp)

    def convert_to_message(self, raw_message: Any) -> IMMessage:
        """将企业微信消息转换为统一消息格式"""
        sender = raw_message.source
        message_elements = []
        raw_message_dict = raw_message.__dict__

        # 处理文本消息
        if raw_message.type == "text":
            text_element = TextMessage(text=raw_message.content)
            message_elements.append(text_element)

        return IMMessage(
            sender=sender,
            message_elements=message_elements,
            raw_message=raw_message_dict
        )

    async def send_message(self, message: IMMessage, recipient: Any):
        """发送消息到企业微信"""
        user_id = recipient
        
        for element in message.message_elements:
            if isinstance(element, TextMessage):
                await self._send_text(user_id, element.text)
            elif isinstance(element, ImageMessage):
                await self._send_image(user_id, element.url)
            elif isinstance(element, VoiceMessage):
                await self._send_voice(user_id, element.url)

    async def _send_text(self, user_id: str, text: str):
        """发送文本消息"""
        try:
            self.client.message.send_text(self.config.agent_id, user_id, text)
        except Exception as e:
            self.logger.error(f"Failed to send text message: {e}")

    async def _send_image(self, user_id: str, image_data: str):
        """发送图片消息"""
        try:
            image_bytes = BytesIO(base64.b64decode(image_data))
            media_id = self.client.media.upload("image", image_bytes)["media_id"]
            self.client.message.send_image(self.config.agent_id, user_id, media_id)
        except Exception as e:
            self.logger.error(f"Failed to send image message: {e}")

    async def _send_voice(self, user_id: str, voice_data: str):
        """发送语音消息"""
        try:
            voice_bytes = BytesIO(base64.b64decode(voice_data))
            media_id = self.client.media.upload("voice", voice_bytes)["media_id"]
            self.client.message.send_voice(self.config.agent_id, user_id, media_id)
        except Exception as e:
            self.logger.error(f"Failed to send voice message: {e}")

    async def start(self):
        """启动服务"""
        from hypercorn.config import Config
        from hypercorn.asyncio import serve

        config = Config()
        config.bind = [f"{self.config.host}:{self.config.port}"]
        config._log = get_logger("Wecom-API")
        
        self.server_task = asyncio.create_task(
            serve(self.app, config)
        )

    async def stop(self):
        """停止服务"""
        if hasattr(self, 'server_task'):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error during server shutdown: {e}")
