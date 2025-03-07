
import asyncio
import uuid
from typing import Optional

import ymbotpy as botpy
import ymbotpy.message
from pydantic import BaseModel, ConfigDict, Field

from kirara_ai.im.adapter import BotProfileAdapter, IMAdapter
from kirara_ai.im.message import ImageMessage, IMMessage, MentionElement, TextMessage, VoiceMessage
from kirara_ai.im.profile import UserProfile
from kirara_ai.im.sender import ChatSender, ChatType
from kirara_ai.logger import get_logger
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.dispatch import WorkflowDispatcher

WEBHOOK_URL_PREFIX = "/im/webhook/qqbot"


def make_webhook_url():
    return f"{WEBHOOK_URL_PREFIX}/{str(uuid.uuid4())[:8]}/"


def auto_generate_webhook_url(s: dict):
    s["readOnly"] = True
    s["default"] = make_webhook_url()
    s["textType"] = True

class QQBotConfig(BaseModel):
    """
    QQBot 配置文件模型。
    """
    app_id: str = Field(description="机器人的 App ID。")
    app_secret: str = Field(title="App Secret", description="机器人的 App Secret。")
    token: str = Field(
        title="Token", description="机器人令牌，用于调用 QQ 机器人的 OpenAPI。")
    sandbox: bool = Field(title="沙盒环境", description="是否为沙盒环境，通常只有正式发布的机器人才会关闭此选项。", default=False)
    webhook_url: str = Field(
        title="Webhook 回调 URL", description="供 QQ 机器人回调的 URL，由系统自动生成，无法修改。",
        default_factory=make_webhook_url,
        json_schema_extra=auto_generate_webhook_url
    )
    model_config = ConfigDict(extra="allow")


class QQBotAdapter(botpy.WebHookClient, IMAdapter, BotProfileAdapter):
    """
    QQBot Adapter，包含 QQBot Bot 的所有逻辑。
    """

    dispatcher: WorkflowDispatcher
    web_server: WebServer
    _loop: asyncio.AbstractEventLoop

    def __init__(self, config: QQBotConfig):
        self.config = config
        self.is_sandbox = config.sandbox
        self.logger = get_logger("QQBot-Adapter")
        super().__init__(timeout=5,
            is_sandbox=self.is_sandbox,
            bot_log=True,
            ext_handlers=True,
        )
        self.loop = self._loop
        self.user = None

    def convert_to_message(self, raw_message: ymbotpy.message.BaseMessage) -> IMMessage:
        """
        将 Telegram 的 Update 对象转换为 Message 对象。
        :param raw_message: Telegram 的 Update 对象。
        :return: 转换后的 Message 对象。
        """
        if isinstance(raw_message, ymbotpy.message.GroupMessage):
            sender = ChatSender.from_group_chat(raw_message.author.member_openid, raw_message.group_openid, 'QQ 用户')
        elif isinstance(raw_message, ymbotpy.message.C2CMessage):
            sender = ChatSender.from_c2c_chat(raw_message.author.user_openid, 'QQ 用户')
        else:
            raise ValueError(f"不支持的消息类型: {type(raw_message)}")
        
        raw_dict = {items: str(getattr(raw_message, items)) for items in raw_message.__slots__ if not items.startswith("_")}
        sender.raw_metadata = {
            "message_id": raw_message.id,
            "message_seq": raw_message.msg_seq,
            "timestamp": raw_message.timestamp,
        }
        elements = []
        if raw_message.content.strip():
            elements.append(TextMessage(text=raw_message.content.lstrip()))
        for attachment in raw_message.attachments:
            if attachment.content_type.startswith('image/'):
                elements.append(ImageMessage(url=attachment.url, format=attachment.content_type.removeprefix('image/')))
            elif attachment.content_type.startswith('audio'):
                elements.append(VoiceMessage(url=attachment.url, format=attachment.filename.split('.')[-1]))
        return IMMessage(sender=sender, message_elements=elements, raw_message=raw_dict)

    async def send_message(self, message: IMMessage, recipient: ChatSender):
        """
        发送消息
        :param message: 要发送的消息对象。
        :param recipient: 接收消息的目标对象。
        """
        if recipient.chat_type == ChatType.C2C:
            await self.api.post_c2c_message(openid=recipient.user_id, msg_id=recipient.raw_metadata.get('message_id'), content=message.content)
        elif recipient.chat_type == ChatType.GROUP:
            await self.api.post_group_message(group_openid=recipient.group_id, msg_id=recipient.raw_metadata.get('message_id'), content=message.content)

    async def on_c2c_message_create(self, message: ymbotpy.message.C2CMessage):
        """
        处理接收到的消息。
        :param message: 接收到的消息对象。
        """
        self.logger.debug(f"收到 C2C 消息: {message}")
        message = self.convert_to_message(message)
        await self.dispatcher.dispatch(self, message)

    async def on_group_at_message_create(self, message: ymbotpy.message.GroupMessage):
        """
        处理接收到的群消息。
        :param message: 接收到的消息对象。
        """
        self.logger.debug(f"收到群消息: {message}")
        message = self.convert_to_message(message)
        # 这个逆天的 Webhook 居然不包含 mention 字段，这里要手动补上
        message.message_elements.append(MentionElement(target=ChatSender.get_bot_sender()))
        await self.dispatcher.dispatch(self, message)
        
    async def get_bot_profile(self) -> Optional[UserProfile]:
        """
        获取机器人资料
        :return: 机器人资料
        """
        if self.user is None:
            return None
        return UserProfile(
            user_id=self.user['id'],
            username=self.user['username'],
            display_name=self.user['username'],
            avatar_url=self.user['avatar']
        )

    async def start(self):
        """启动 Bot"""
        
        token = botpy.Token(self.config.app_id, self.config.app_secret)
        self.user = await self.http.login(token)
        self.robot = botpy.Robot(self.user)

        bot_webhook = botpy.BotWebHook(
            self.config.app_id, 
            self.config.app_secret,
            hook_route='/',
            client=self,
            system_log=True,
            botapi=self.api,
            loop=self.loop
        )

        app = await bot_webhook.init_fastapi()
        app.user_middleware.clear()
        self.web_server.mount_app(self.config.webhook_url.removesuffix('/'), app)

    async def stop(self):
        """停止 Bot"""