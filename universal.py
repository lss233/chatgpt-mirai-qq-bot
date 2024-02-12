import asyncio
import re
from typing import Callable

import httpcore
import httpx
import openai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from httpx import ConnectTimeout
from loguru import logger
from requests.exceptions import SSLError, ProxyError, RequestException
from urllib3.exceptions import MaxRetryError

from constants import botManager, BotPlatform
from constants import config
from conversation import ConversationHandler, ConversationContext
from exceptions import PresetNotFoundException, BotRatelimitException, ConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, BotOperationNotSupportedException, CommandRefusedException, \
    DrawingFailedException
from middlewares.baiducloud import MiddlewareBaiduCloud
from middlewares.concurrentlock import MiddlewareConcurrentLock
from middlewares.ratelimit import MiddlewareRatelimit
from middlewares.timeout import MiddlewareTimeout
from utils.text_to_speech import get_tts_voice, TtsVoiceManager, VoiceType

middlewares = [MiddlewareTimeout(), MiddlewareRatelimit(), MiddlewareBaiduCloud(), MiddlewareConcurrentLock()]


async def get_ping_response(conversation_context: ConversationContext):
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


async def handle_message(_respond: Callable, session_id: str, message: str,
                         chain: MessageChain = MessageChain("Unsupported"), is_manager: bool = False,
                         nickname: str = '某人', request_from=BotPlatform.AriadneBot):
    conversation_context = None

    def wrap_request(n, m):
        """
        Wrapping send messages
        """
        async def call(session_id, message, conversation_context, respond):
            await m.handle_request(session_id, message, respond, conversation_context, n)

        return call

    def wrap_respond(n, m):
        """
        Wrapping respond messages
        """
        async def call(session_id, message, rendered, respond):
            await m.handle_respond(session_id, message, rendered, respond, n)

        return call

    async def respond(msg: str):
        """
        Respond method
        """
        if not msg:
            return
        ret = await _respond(msg)
        for m in middlewares:
            await m.on_respond(session_id, message, msg)

        # TODO: 之后重构成 platforms 的 respond 只处理 MessageChain
        if isinstance(msg, str):
            msg = MessageChain([Plain(msg)])

        nonlocal conversation_context
        if not conversation_context:
            try:
                conversation_context = conversation_handler.current_conversation
            except NameError:
                logger.warning(f"收到空消息时尚未定义conversation_handler，报错已忽略")

        if not conversation_context:
            return ret
        # TTS Converting
        if conversation_context.conversation_voice and isinstance(msg, MessageChain):
            if request_from in [BotPlatform.Onebot, BotPlatform.AriadneBot]:
                voice_type = VoiceType.Silk
            elif request_from == BotPlatform.HttpService:
                voice_type = VoiceType.Mp3
            else:
                voice_type = VoiceType.Wav
            tasks = []
            for elem in msg:
                task = asyncio.create_task(get_tts_voice(elem, conversation_context, voice_type))
                tasks.append(task)
            while tasks:
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for voice_task in done:
                    voice = await voice_task
                    if voice:
                        await _respond(voice)

        return ret

    async def request(_session_id, prompt: str, conversation_context, _respond):
        """
        Request method
        """

        task = None

        # 不带前缀 - 正常初始化会话
        if bot_type_search := re.search(config.trigger.switch_command, prompt):
            if not (config.trigger.allow_switching_ai or is_manager):
                await respond("不好意思，只有管理员才能切换AI！")
                return
            conversation_handler.current_conversation = (
                await conversation_handler.create(
                    bot_type_search[1].strip()
                )
            )
            await respond(f"已切换至 {bot_type_search[1].strip()} AI，现在开始和我聊天吧！")
            return
        # 最终要选择的对话上下文
        if not conversation_context:
            conversation_context = conversation_handler.current_conversation
        # 此处为会话存在后可执行的指令

        # 重置会话
        if prompt in config.trigger.reset_command:
            task = conversation_context.reset()

        elif prompt in config.trigger.rollback_command:
            task = conversation_context.rollback()

        elif prompt in config.trigger.ping_command:
            await respond(await get_ping_response(conversation_context))
            return

        elif voice_type_search := re.search(config.trigger.switch_voice, prompt):
            if not config.azure.tts_speech_key and config.text_to_speech.engine == "azure":
                await respond("未配置 Azure TTS 账户，无法切换语音！")
            new_voice = voice_type_search[1].strip()
            if new_voice in ['关闭', "None"]:
                conversation_context.conversation_voice = None
                await respond("已关闭语音，让我们继续聊天吧！")
            elif config.text_to_speech.engine == "vits":
                from utils.vits_tts import vits_api_instance
                try:
                    voice_name = await vits_api_instance.set_id(new_voice)
                    conversation_context.conversation_voice = TtsVoiceManager.parse_tts_voice("vits", voice_name)
                    await respond(f"已切换至 {voice_name} 语音，让我们继续聊天吧！")
                except ValueError:
                    await respond("提供的语音ID无效，请输入一个有效的数字ID。")
                except Exception as e:
                    await respond(str(e))
            elif config.text_to_speech.engine == "edge":
                tts_voice = TtsVoiceManager.parse_tts_voice("edge", new_voice)
                if tts_voice:
                    conversation_context.conversation_voice = tts_voice
                    await respond(f"已切换至 {tts_voice.alias} 语音，让我们继续聊天吧！")
                else:
                    available_voice = ",".join([v.alias for v in await TtsVoiceManager.list_tts_voices(
                        "edge", config.text_to_speech.default_voice_prefix)])
                    await respond(f"提供的语音ID无效，请输入一个有效的语音ID。如：{available_voice}。")
                    conversation_context.conversation_voice = None
            elif config.text_to_speech.engine == "azure":
                tts_voice = TtsVoiceManager.parse_tts_voice("azure", new_voice)
                conversation_context.conversation_voice = tts_voice
                if tts_voice:
                    await respond(f"已切换至 {tts_voice.full_name} 语音，让我们继续聊天吧！")
                else:
                    await respond("提供的语音ID无效，请输入一个有效的语音ID。")
            else:
                await respond("未配置文字转语音引擎，无法使用语音功能。")
            return

        elif prompt in config.trigger.mixed_only_command:
            conversation_context.switch_renderer("mixed")
            await respond("已切换至图文混合模式，接下来我的回复将会以图文混合的方式呈现！")
            return

        elif prompt in config.trigger.image_only_command:
            conversation_context.switch_renderer("image")
            await respond("已切换至纯图片模式，接下来我的回复将会以图片呈现！")
            return

        elif prompt in config.trigger.text_only_command:
            conversation_context.switch_renderer("text")
            await respond("已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")
            return

        elif switch_model_search := re.search(config.trigger.switch_model, prompt):
            model_name = switch_model_search[1].strip()
            if model_name in conversation_context.supported_models:
                if not (is_manager or model_name in config.trigger.allowed_models):
                    await respond(f"不好意思，只有管理员才能切换到 {model_name} 模型！")
                else:
                    await conversation_context.switch_model(model_name)
                    await respond(f"已切换至 {model_name} 模型，让我们聊天吧！")
            else:
                logger.warning(f"模型 {model_name} 不在支持列表中，下次将尝试使用此模型创建对话。")
                await conversation_context.switch_model(model_name)
                await respond(
                    f"模型 {model_name} 不在支持列表中，下次将尝试使用此模型创建对话，目前AI仅支持：{conversation_context.supported_models}！")
            return

        # 加载预设
        if preset_search := re.search(config.presets.command, prompt):
            logger.trace(f"{session_id} - 正在执行预设： {preset_search[1]}")
            async for _ in conversation_context.reset(): ...
            task = conversation_context.load_preset(preset_search[1])
        elif not conversation_context.preset:
            # 当前没有预设
            logger.trace(f"{session_id} - 未检测到预设，正在执行默认预设……")
            # 隐式加载不回复预设内容
            async for _ in conversation_context.load_preset('default'): ...

        # 没有任务那就聊天吧！
        if not task:
            task = conversation_context.ask(prompt=prompt, chain=chain, name=nickname)
        async for rendered in task:
            if rendered:
                if not str(rendered).strip():
                    logger.warning("检测到内容为空的输出，已忽略")
                    continue
                action = lambda session_id, prompt, rendered, respond: respond(rendered)
                for m in middlewares:
                    action = wrap_respond(action, m)

                # 开始处理 handle_response
                await action(session_id, prompt, rendered, respond)
        for m in middlewares:
            await m.handle_respond_completed(session_id, prompt, respond)

    try:
        if not message.strip():
            return await respond(config.response.placeholder)

        for r in config.trigger.ignore_regex:
            if re.match(r, message):
                logger.debug(f"此消息满足正则表达式： {r}，忽略……")
                return

        # 此处为会话不存在时可以执行的指令
        conversation_handler = await ConversationHandler.get_handler(session_id)
        # 指定前缀对话
        if ' ' in message and (config.trigger.allow_switching_ai or is_manager):
            for ai_type, prefixes in config.trigger.prefix_ai.items():
                for prefix in prefixes:
                    if f'{prefix} ' in message:
                        conversation_context = await conversation_handler.first_or_create(ai_type)
                        message = message.removeprefix(f'{prefix} ')
                        break
                else:
                    # Continue if the inner loop wasn't broken.
                    continue
                # Inner loop was broken, break the outer.
                break
        if not conversation_handler.current_conversation:
            conversation_handler.current_conversation = await conversation_handler.create(
                config.response.default_ai)

        action = request
        for m in middlewares:
            action = wrap_request(action, m)

        # 开始处理
        await action(session_id, message.strip(), conversation_context, respond)
    except DrawingFailedException as e:
        logger.exception(e)
        await _respond(config.response.error_drawing.format(exc=e.__cause__ or '未知'))
    except CommandRefusedException as e:
        await _respond(str(e))
    except openai.error.InvalidRequestError as e:
        await _respond(f"服务器拒绝了您的请求，原因是： {str(e)}")
    except BotOperationNotSupportedException:
        await _respond("暂不支持此操作，抱歉！")
    except ConcurrentMessageException as e:  # Chatbot 账号同时收到多条消息
        await _respond(config.response.error_request_concurrent_error)
    except BotRatelimitException as e:  # Chatbot 账号限流
        await _respond(config.response.error_request_too_many.format(exc=e))
    except NoAvailableBotException as e:  # 预设不存在
        await _respond(f"当前没有可用的{e}账号，不支持使用此 AI！")
    except BotTypeNotFoundException as e:  # 预设不存在
        respond_msg = f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n"
        respond_msg += botManager.bots_info()
        await _respond(respond_msg)
    except PresetNotFoundException:  # 预设不存在
        await _respond("预设不存在，请检查你的输入是否有问题！")
    except (RequestException, SSLError, ProxyError, MaxRetryError, ConnectTimeout, ConnectTimeout,
            httpcore.ReadTimeout, httpx.TimeoutException) as e:  # 网络异常
        await _respond(config.response.error_network_failure.format(exc=e))
    except Exception as e:  # 未处理的异常
        logger.exception(e)
        await _respond(config.response.error_format.format(exc=e))
