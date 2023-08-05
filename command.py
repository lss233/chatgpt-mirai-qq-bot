import re
from constants import config, botManager
from loguru import logger

from utils.text_to_speech import TtsVoiceManager


class CommandContext:
    def __init__(self, args, session_id, conversation_context, conversation_handler, respond, is_manager, task):
        self.args = args
        """命令的参数"""
        self.session_id = session_id
        """当前会话的ID"""
        self.conversation_context = conversation_context
        """当前会话的上下文"""
        self.conversation_handler = conversation_handler
        """当前会话的处理器"""
        self.respond = respond
        """回复消息的方法"""
        self.is_manager = is_manager
        """是否为管理员"""
        self.task = task
        """当前会话的任务"""


class CommandHandler:
    """
    命令处理器
    不需要处理任务的返回True
    需要处理任务的返回False
    """
    def __init__(self):
        self.commands = {
            r"切换模型 (.+)": self.handle_switch_model,
            r"切换AI (.+)": self.handle_switch_ai,
            r"切换语音 (.+)": self.handle_switch_voice,
            r"重置会话": self.handle_reset_conversation,
            r"回滚会话": self.handle_rollback_command,
            r"图文混合模式": self.handle_mixed_only_command,
            r"图片模式": self.handle_image_only_command,
            r"文本模式": self.handle_text_only_command,
            r"帮助|help": self.handle_help,
            r"ping": self.handle_ping_command,
            r"加载预设 (.+)": self.handle_load_preset_command,
        }
        self.command_descriptions = {
            r"切换模型 (.+)": "切换当前上下文的模型，例如：切换模型 gpt-4",
            r"切换AI (.+)": "切换AI的命令，例如：切换AI chatgpt-web",
            r"切换语音 (.+)": "切换tts语音音色的命令，例如：切换语音 zh-CN-XiaoxiaoNeural",
            r"重置会话": "重置当前上下文的会话",
            r"回滚会话": "回滚当前上下文的会话",
            r"图文混合模式": "切换当前上下文的渲染模式为图文混合模式",
            r"图片模式": "切换当前上下文的渲染模式为图片模式",
            r"文本模式": "切换当前上下文的渲染模式为文本模式",
            r"帮助|help": "显示所有指令",
        }

    async def get_ping_response(self, conversation_context):
        current_voice = conversation_context.conversation_voice.alias if conversation_context.conversation_voice else "无"
        response = config.response.ping_response.format(current_ai=conversation_context.type,
                                                        current_voice=current_voice,
                                                        supported_ai=botManager.bots_info())
        tts_voices = await TtsVoiceManager.list_tts_voices(
            config.text_to_speech.engine, config.text_to_speech.default_voice_prefix)
        if tts_voices:
            supported_tts = ",".join([v.alias for v in tts_voices])
            response += config.response.ping_tts_response.format(supported_tts=supported_tts)
        return response

    async def handle_load_preset_command(self, context):
        preset_name = context.args[0]
        logger.trace(f"{context.session_id} - 正在执行预设： {preset_name}")
        async for _ in context.conversation_context.reset(): ...
        context.task[0] = context.conversation_context.load_preset(preset_name)
        if not context.conversation_context.preset:
            # 当前没有预设
            logger.trace(f"{context.session_id} - 未检测到预设，正在执行默认预设……")
            # 隐式加载不回复预设内容
            async for _ in context.conversation_context.load_preset('default'): ...
        return False

    async def handle_ping_command(self, context):
        await context.respond(await self.get_ping_response(context.conversation_context))
        return True

    async def handle_help(self, context):
        help_text = ""
        for command, handler in self.commands.items():
            if command == "帮助|help":
                continue
            description = self.command_descriptions.get(command, "")
            help_text += f"{command}: {description}\n"
        await context.respond(help_text)
        return True

    async def handle_mixed_only_command(self, context):
        context.conversation_context.switch_renderer("mixed")
        await context.respond("已切换至图文混合模式，接下来我的回复将会以图文混合的方式呈现！")
        return True

    async def handle_image_only_command(self, context):
        context.conversation_context.switch_renderer("image")
        await context.respond("已切换至纯图片模式，接下来我的回复将会以图片呈现！")
        return True

    async def handle_text_only_command(self, context):
        context.conversation_context.switch_renderer("text")
        await context.respond("已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")
        return True

    async def handle_switch_model(self, context):
        model_name = context.args[0]
        if model_name in context.conversation_context.supported_models:
            if not (context.is_manager or model_name in config.trigger.allowed_models):
                await context.respond(f"不好意思，只有管理员才能切换到 {model_name} 模型！")
            else:
                await context.conversation_context.switch_model(model_name)
                await context.respond(f"已切换至 {model_name} 模型，让我们聊天吧！")
        else:
            logger.warning(f"模型 {model_name} 不在支持列表中，下次将尝试使用此模型创建对话。")
            await context.conversation_context.switch_model(model_name)
            await context.respond(
                f"模型 {model_name} 不在支持列表中，下次将尝试使用此模型创建对话，目前AI仅支持：{conversation_context.supported_models}！")
        return True

    async def handle_switch_ai(self, context):
        bot_type_search = context.args[0]
        if not (config.trigger.allow_switching_ai or context.is_manager):
            await context.respond("不好意思，只有管理员才能切换AI！")
            return False
        context.conversation_handler.current_conversation = (
            await context.conversation_handler.create(
                bot_type_search
            )
        )
        await context.respond(f"已切换至 {bot_type_search} AI，现在开始和我聊天吧！")
        return True

    async def handle_switch_voice(self, context):
        voice_name = context.args[0]
        if not config.azure.tts_speech_key and config.text_to_speech.engine == "azure":
            await context.respond("未配置 Azure TTS 账户，无法切换语音！")
        new_voice = voice_name
        if new_voice in ['关闭', "None"]:
            context.conversation_context.conversation_voice = None
            await context.respond("已关闭语音，让我们继续聊天吧！")
        elif config.text_to_speech.engine == "vits":
            from utils.vits_tts import vits_api_instance
            try:
                voice_name = await vits_api_instance.set_id(new_voice)
                context.conversation_context.conversation_voice = TtsVoiceManager.parse_tts_voice("vits", voice_name)
                await context.respond(f"已切换至 {voice_name} 语音，让我们继续聊天吧！")
            except ValueError:
                await context.respond("提供的语音ID无效，请输入一个有效的数字ID。")
            except Exception as e:
                await context.respond(str(e))
        elif config.text_to_speech.engine == "edge":
            tts_voice = TtsVoiceManager.parse_tts_voice("edge", new_voice)
            if tts_voice:
                context.conversation_context.conversation_voice = tts_voice
                await context.respond(f"已切换至 {tts_voice.alias} 语音，让我们继续聊天吧！")
            else:
                available_voice = ",".join([v.alias for v in await TtsVoiceManager.list_tts_voices(
                    "edge", config.text_to_speech.default_voice_prefix)])
                await context.respond(f"提供的语音ID无效，请输入一个有效的语音ID。如：{available_voice}。")
                context.conversation_context.conversation_voice = None
        elif config.text_to_speech.engine == "azure":
            tts_voice = TtsVoiceManager.parse_tts_voice("azure", new_voice)
            context.conversation_context.conversation_voice = tts_voice
            if tts_voice:
                await context.respond(f"已切换至 {tts_voice.full_name} 语音，让我们继续聊天吧！")
            else:
                await context.respond("提供的语音ID无效，请输入一个有效的语音ID。")
        else:
            await context.respond("未配置文字转语音引擎，无法使用语音功能。")
        return True

    async def handle_reset_conversation(self, context):
        context.task[0] = context.conversation_context.reset()
        return False

    async def handle_rollback_command(self, context):
        context.task[0] = context.conversation_context.rollback()
        return False

    async def handle_command(self, prompt, session_id, conversation_context, conversation_handler, respond, is_manager, task):
        for command_regex, handler in self.commands.items():
            match = re.search(command_regex, prompt)
            if match:
                args = match.groups()
                context = CommandContext(args, session_id, conversation_context, conversation_handler, respond,
                                         is_manager, task)
                return await handler(context)
        return False
