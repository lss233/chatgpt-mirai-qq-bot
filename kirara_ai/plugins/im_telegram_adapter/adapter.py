import asyncio
import random
from functools import lru_cache

import telegramify_markdown
from pydantic import BaseModel, ConfigDict, Field
from telegram import Bot, Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from kirara_ai.im.adapter import EditStateAdapter, IMAdapter, UserProfileAdapter
from kirara_ai.im.message import ImageMessage, IMMessage, MentionElement, TextMessage, VoiceMessage
from kirara_ai.im.profile import Gender, UserProfile
from kirara_ai.im.sender import ChatSender, ChatType
from kirara_ai.logger import get_logger
from kirara_ai.workflow.core.dispatch import WorkflowDispatcher


def get_display_name(user: User):
    if user.username:
        return user.username
    elif user.first_name or user.last_name:
        return f"{user.first_name} {user.last_name}".strip()
    else:
        return user.id


class TelegramConfig(BaseModel):
    """
    Telegram 配置文件模型。
    """

    token: str = Field(description="Telegram Bot Token")
    model_config = ConfigDict(extra="allow")

    def __repr__(self):
        return f"TelegramConfig(token={self.token})"


class TelegramAdapter(IMAdapter, UserProfileAdapter, EditStateAdapter):
    """
    Telegram Adapter，包含 Telegram Bot 的所有逻辑。
    """

    dispatcher: WorkflowDispatcher

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.application = Application.builder().token(config.token).build()
        self.bot = Bot(token=config.token)
        # 注册命令处理器和消息处理器
        self.application.add_handler(CommandHandler("start", self.command_start))
        self.application.add_handler(
            MessageHandler(
                filters.TEXT | filters.VOICE | filters.PHOTO, self.handle_message
            )
        )
        self.logger = get_logger("Telegram-Adapter")

    async def command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        await update.message.reply_text("Welcome! I am ready to receive your messages.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理接收到的消息"""
        # 将 Telegram 消息转换为 Message 对象
        message = self.convert_to_message(update)
        try:
            await self.dispatcher.dispatch(self, message)
        except Exception as e:
            await update.message.reply_text(
                f"Workflow execution failed, please try again later: {str(e)}"
            )

    def convert_to_message(self, raw_message: Update) -> IMMessage:
        """
        将 Telegram 的 Update 对象转换为 Message 对象。
        :param raw_message: Telegram 的 Update 对象。
        :return: 转换后的 Message 对象。
        """
        if (
            raw_message.message.chat.type == "group"
            or raw_message.message.chat.type == "supergroup"
        ):
            sender = ChatSender.from_group_chat(
                user_id=raw_message.message.from_user.id,
                group_id=raw_message.message.chat_id,
                display_name=get_display_name(raw_message.message.from_user),
            )
        else:
            sender = ChatSender.from_c2c_chat(
                user_id=raw_message.message.chat_id,
                display_name=get_display_name(raw_message.message.from_user),
            )

        message_elements = []
        raw_message_dict = raw_message.message.to_dict()
        # 处理文本消息
        if raw_message.message.text:
            text = raw_message.message.text
            offset = 0
            for entity in raw_message.message.entities or []:
                if entity.type in ("mention", "text_mention"):
                    # Extract mention text
                    mention_text = text[entity.offset:entity.offset + entity.length]

                    # Add preceding text as TextMessage
                    if entity.offset > offset:
                        message_elements.append(TextMessage(text=text[offset:entity.offset]))

                    # Create ChatSender for MentionElement
                    if entity.type == "text_mention" and entity.user:
                        if entity.user.id == self.me.id:
                            mention_element = MentionElement(target=ChatSender.get_bot_sender())
                        else:
                            mention_element = MentionElement(target=ChatSender.from_c2c_chat(user_id=entity.user.id, display_name=mention_text))
                    elif entity.type == "mention":
                        # 这里需要从 adapter 实例中获取 bot 的 username
                        if mention_text == f'@{self.me.username}':
                            mention_element = MentionElement(target=ChatSender.get_bot_sender())
                        else:
                            mention_element = MentionElement(target=ChatSender.from_c2c_chat(user_id=f'unknown_id:{mention_text}', display_name=mention_text))
                    else:
                        # Fallback in case of unknown entity type
                        mention_element = TextMessage(text=mention_text)  # Or handle as needed
                    message_elements.append(mention_element)

                    offset = entity.offset + entity.length

            # Add remaining text as TextMessage
            if offset < len(text):
                message_elements.append(TextMessage(text=text[offset:]))

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
        message = IMMessage(
            sender=sender,
            message_elements=message_elements,
            raw_message=raw_message_dict,
        )
        print(message)
        return message

    async def send_message(self, message: IMMessage, recipient: ChatSender):
        """
        发送消息到 Telegram。
        :param message: 要发送的消息对象。
        :param recipient: 接收消息的目标对象，这里应该是 chat_id。
        """
        if recipient.chat_type == ChatType.C2C:
            chat_id = recipient.user_id
        elif recipient.chat_type == ChatType.GROUP:
            chat_id = recipient.group_id
        else:
            raise ValueError(f"Unsupported chat type: {recipient.chat_type}")

        for element in message.message_elements:
            if isinstance(element, TextMessage):
                await self.application.bot.send_chat_action(
                    chat_id=chat_id, action="typing"
                )
                text = telegramify_markdown.markdownify(element.text)
                # 如果是非首条消息，适当停顿，模拟打字
                if message.message_elements.index(element) > 0:
                    # 停顿通常和字数有关，但是会带一些随机
                    duration = len(element.text) * 0.1 + random.uniform(0, 1) * 0.1
                    await asyncio.sleep(duration)
                await self.application.bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="MarkdownV2"
                )

            elif isinstance(element, ImageMessage):
                await self.application.bot.send_chat_action(
                    chat_id=chat_id, action="upload_photo"
                )
                await self.application.bot.send_photo(
                    chat_id=chat_id, photo=element.url, parse_mode="MarkdownV2"
                )
            elif isinstance(element, VoiceMessage):
                await self.application.bot.send_chat_action(
                    chat_id=chat_id, action="upload_voice"
                )
                await self.application.bot.send_voice(
                    chat_id=chat_id, voice=element.url, parse_mode="MarkdownV2"
                )

    async def start(self):
        """启动 Bot"""
        await self.application.initialize()
        await self.application.start()
        self.me = await self.bot.get_me()
        await self.application.updater.start_polling(drop_pending_updates=True)

    async def stop(self):
        """停止 Bot"""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    async def set_chat_editing_state(
        self, chat_sender: ChatSender, is_editing: bool = True
    ):
        """
        设置或取消对话的编辑状态
        :param chat_sender: 对话的发送者
        :param is_editing: True 表示正在编辑，False 表示取消编辑状态
        """
        action = "typing" if is_editing else "cancel"
        chat_id = (
            chat_sender.user_id
            if chat_sender.chat_type == ChatType.C2C
            else chat_sender.group_id
        )
        try:
            self.logger.debug(
                f"Setting chat editing state to {is_editing} for chat_id {chat_id}"
            )
            if is_editing:
                await self.application.bot.send_chat_action(
                    chat_id=chat_id, action=action
                )
            else:
                # 取消编辑状态时发送一个空操作
                await self.application.bot.send_chat_action(
                    chat_id=chat_id, action=action
                )
        except Exception as e:
            self.logger.warning(f"Failed to set chat editing state: {str(e)}")

    @lru_cache(maxsize=10)
    async def _cached_get_chat(self, user_id):
        """
        带缓存的获取用户信息方法
        :param user_id: 用户ID
        :return: 用户对象
        """
        return await self.application.bot.get_chat(user_id)

    async def query_user_profile(self, chat_sender: ChatSender) -> UserProfile:
        """
        查询 Telegram 用户资料
        :param chat_sender: 用户的聊天发送者信息
        :return: 用户资料
        """
        try:
            # 获取用户 ID
            user_id = chat_sender.user_id
            # 获取用户对象（使用缓存）
            user = await self._cached_get_chat(user_id)

            # 确定性别
            gender = Gender.UNKNOWN
            if hasattr(user, "gender"):
                if user.gender == "male":
                    gender = Gender.MALE
                elif user.gender == "female":
                    gender = Gender.FEMALE

            # 构建用户资料
            profile = UserProfile(
                user_id=str(user_id),
                username=user.username,
                display_name=get_display_name(user),
                full_name=f"{user.first_name or ''} {user.last_name or ''}".strip(),
                gender=gender,
                avatar_url=None,  # Telegram 需要额外处理获取头像
                language=user.language_code,
                extra_info={
                    "is_bot": user.is_bot,
                    "is_premium": getattr(user, "is_premium", False),
                },
            )

            return profile

        except Exception as e:
            self.logger.warning(f"Failed to query user profile: {str(e)}")
            # 返回部分信息
            return UserProfile(
                user_id=str(chat_sender.user_id), display_name=chat_sender.display_name
            )
