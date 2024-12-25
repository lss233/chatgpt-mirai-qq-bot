from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from framework.im.adapter import IMAdapter
from framework.im.message import Message, TextMessage, VoiceMessage, ImageMessage
from framework.im.telegram.config import TelegramConfig
from framework.llm.llm_registry import LLMAbility

class TelegramAdapter(IMAdapter):
    """
    Telegram Adapter，包含 Telegram Bot 的所有逻辑。
    """

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.application = Application.builder().token(config.token).build()

        # 注册命令处理器和消息处理器
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT | filters.VOICE | filters.PHOTO, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        await update.message.reply_text("Welcome! I am ready to receive your messages.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理接收到的消息"""
        # 将 Telegram 消息转换为 Message 对象
        message = self.convert_to_message(update)

        # 打印转换后的 Message 对象
        print("Converted Message:", message.to_dict())

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理接收到的消息"""
        # 将 Telegram 消息转换为 Message 对象
        message = self.convert_to_message(update)

        # 打印转换后的 Message 对象
        print("Converted Message:", message.to_dict())

    def convert_to_message(self, raw_message: Update) -> Message:
        """
        将 Telegram 的 Update 对象转换为 Message 对象。
        :param raw_message: Telegram 的 Update 对象。
        :return: 转换后的 Message 对象。
        """
        sender = raw_message.message.from_user.username or raw_message.message.from_user.first_name
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
        message = Message(sender=sender, message_elements=message_elements, raw_message=raw_message_dict)
        return message


    def run(self):
        """启动 Bot"""
        self.application.run_polling()

    def stop(self):
        """停止 Bot"""
        self.application.stop()