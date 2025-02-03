import re
from typing import Any
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage, TextMessage, VoiceMessage, ImageMessage
from framework.logger import get_logger
from framework.workflow_dispatcher.workflow_dispatcher import WorkflowDispatcher

from pydantic import ConfigDict, BaseModel, Field
import telegramify_markdown

class TelegramConfig(BaseModel):
    """
    Telegram 配置文件模型。
    """
    token: str = Field(description="Telegram Bot Token")
    model_config = ConfigDict(extra="allow")

    def __repr__(self):
        return f"TelegramConfig(token={self.token})"
    
class TelegramAdapter(IMAdapter):
    """
    Telegram Adapter，包含 Telegram Bot 的所有逻辑。
    """
    dispatcher: WorkflowDispatcher

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.application = (
            Application.builder()
            .token(config.token)
            .build()
        )

        # 注册命令处理器和消息处理器
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.PHOTO, self.handle_message))
        self.logger = get_logger("Telegram-Adapter")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        await update.message.reply_text("Welcome! I am ready to receive your messages.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理接收到的消息"""
        # 将 Telegram 消息转换为 Message 对象
        message = self.convert_to_message(update)

        await self.dispatcher.dispatch(self, message)
        # 打印转换后的 Message 对象
        print("Converted Message:", message.to_dict())

    def convert_to_message(self, raw_message: Update) -> IMMessage:
        """
        将 Telegram 的 Update 对象转换为 Message 对象。
        :param raw_message: Telegram 的 Update 对象。
        :return: 转换后的 Message 对象。
        """
        sender = raw_message.message.chat_id
        message_elements = []
        raw_message_dict = raw_message.message.to_dict()

        # 处理文本消息
        if raw_message.message.text:
            text_element = TextMessage(text=raw_message.message.text)
            message_elements.append(text_element)

        # 处理语音消息
        if raw_message.message.voice:
            voice_file = raw_message.message.voice.get_file()
            voice_url = voice_file.file_path
            voice_element = VoiceMessage(url=voice_url)
            message_elements.append(voice_element)

        # 处理图片消息
        if raw_message.message.photo:
            # 获取最高分辨率的图片
            photo = raw_message.message.photo[-1]
            photo_file = photo.get_file()
            photo_url = photo_file.file_path
            photo_element = ImageMessage(url=photo_url)
            message_elements.append(photo_element)

        # 创建 Message 对象
        message = IMMessage(sender=sender, message_elements=message_elements, raw_message=raw_message_dict)
        return message

    async def send_message(self, message: IMMessage, recipient: Any):
        """
        发送消息到 Telegram。
        :param message: 要发送的消息对象。
        :param recipient: 接收消息的目标对象，这里应该是 chat_id。
        """
        chat_id = recipient
        
        for element in message.message_elements:
            if isinstance(element, TextMessage):
                text = telegramify_markdown.markdownify(element.text)
                await self.application.bot.send_message(chat_id=chat_id, text=text, parse_mode="MarkdownV2")
            elif isinstance(element, ImageMessage):
                await self.application.bot.send_photo(chat_id=chat_id, photo=element.url, parse_mode="MarkdownV2")
            elif isinstance(element, VoiceMessage):
                await self.application.bot.send_voice(chat_id=chat_id, voice=element.url, parse_mode="MarkdownV2")

    async def start(self):
        """启动 Bot"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

    async def stop(self):
        """停止 Bot"""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
    
    async def set_chat_editing_state(self, chat_id: int, is_editing: bool = True):
        """
        设置或取消对话的编辑状态
        :param chat_id: Telegram 聊天 ID
        :param is_editing: True 表示正在编辑，False 表示取消编辑状态
        """
        action = "typing" if is_editing else "cancel"
        try:
            self.logger.debug(f"Setting chat editing state to {is_editing} for chat_id {chat_id}")
            if is_editing:
                await self.application.bot.send_chat_action(chat_id=chat_id, action=action)
            else:
                # 取消编辑状态时发送一个空操作
                await self.application.bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception as e:
            self.logger.warning(f"Failed to set chat editing state: {str(e)}")
