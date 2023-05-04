import functools

import asyncio
import re
from typing import Callable, Optional

import httpcore
import httpx
import openai
from graia.ariadne.message.chain import MessageChain
from httpx import ConnectTimeout
from loguru import logger
from requests.exceptions import SSLError, ProxyError, RequestException
from urllib3.exceptions import MaxRetryError

from constants import BotPlatform
import constants
from framework.conversation import ConversationHandler, ConversationContext
from framework.exceptions import PresetNotFoundException, LlmRateLimitException, LlmConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, LlmOperationNotSupportedException, CommandRefusedException, \
    DrawingFailedException
from framework.messages import ImageElement
from framework.middlewares.baiducloud import MiddlewareBaiduCloud
from framework.middlewares.concurrentlock import MiddlewareConcurrentLock
from framework.middlewares.ratelimit import MiddlewareRatelimit
from framework.middlewares.timeout import MiddlewareTimeout
from framework.tts.tts import TTSResponse

middlewares = [MiddlewareTimeout(), MiddlewareRatelimit(), MiddlewareBaiduCloud(), MiddlewareConcurrentLock()]


def __wrap_request(next_, middleware):
    """
    Wrapping send messages
    """

    async def call(session_id, message, conversation_context, respond):
        await middleware.handle_request(session_id, message, respond, conversation_context, next_)

    return call


def __wrap_respond(next_, middleware):
    """
    Wrapping respond messages
    """

    async def call(session_id, message, rendered, respond):
        await middleware.handle_respond(session_id, message, rendered, respond, next_)

    return call


async def reply(bind: Callable, chain: MessageChain = None, text: str = None, voice: TTSResponse = None, image: ImageElement = None):
    """
    Trick: 将方法重定向
    """
    await bind(chain, text, voice, image)


async def handle_message(_respond: Callable, session_id: str, prompt: str,
                         chain: MessageChain = MessageChain("Unsupported"), is_manager: bool = False,
                         nickname: str = '某人', request_from=BotPlatform.AriadneBot):
    """
    Steps:
    1. 获得消息上下文管理器
    2. 从消息上下文管理器获得当前的消息上下文
    3. 判断是否为指令
    4. 发送给 LLM


    """
    try:
        # 跳过空消息
        if not prompt.strip():
            await _respond(constants.config.response.placeholder)
            return

        _initialization = False

        _no_follow = False

        # 跳过要被忽略的消息
        for r in constants.config.trigger.ignore_regex:
            if re.match(r, prompt):
                logger.debug(f"此消息满足正则表达式： {r}，忽略……")
                return

        # 消息上下文
        conversation_context: Optional[ConversationContext] = None

        # 获得消息上下文管理器
        conversation_handler: ConversationHandler = await ConversationHandler.get_handler(session_id)

        # TODO: 统一的指令系统

        # 切换 AI 的指令
        if bot_type_search := re.search(constants.config.trigger.switch_command, prompt):
            if not (constants.config.trigger.allow_switching_ai or is_manager):
                # TODO: option to modify this
                await _respond("不好意思，只有管理员才能切换AI！")
                return
            conversation_handler.current_conversation = (
                await conversation_handler.first_or_create(
                    bot_type_search[1].strip()
                )
            )
            # TODO: option to modify this
            await _respond(f"已切换至 {bot_type_search[1].strip()} AI，现在开始和我聊天吧！")
            return

        # 指定前缀对话
        if ' ' in prompt and (constants.config.trigger.allow_switching_ai or is_manager):
            for ai_type, prefixes in constants.config.trigger.prefix_ai.items():
                for prefix in prefixes:
                    if f'{prefix}' in prompt:
                        conversation_context = await conversation_handler.first_or_create(ai_type)
                        prompt = prompt.removeprefix(f'{prefix}').strip()
                        break
                else:
                    # Continue if the inner loop wasn't broken.
                    continue
                # Inner loop was broken, break the outer.
                break

        if not conversation_handler.current_conversation:
            logger.debug(f"尝试使用 default_ai={constants.config.response.default_ai} 来创建对话上下文")
            conversation_handler.current_conversation = await conversation_handler.create(
                constants.config.response.default_ai)

        # 最终我们要操作的是 conversation_context
        if not conversation_context:
            conversation_context = conversation_handler.current_conversation

        # 重置会话
        if prompt in constants.config.trigger.reset_command:
            await conversation_context.reset()
            # TODO: export to config file
            return await _respond("会话已重置！")

        # 回滚会话
        elif prompt in constants.config.trigger.rollback_command:
            await _respond(
                constants.config.response.rollback_success if await conversation_context.rollback() else constants.config.response.rollback_fail.format(
                    reset=constants.config.trigger.reset_command))

        # ping
        elif prompt in constants.config.trigger.ping_command:
            # TODO: standardlize this
            # await _respond(await get_ping_response(conversation_context))
            return

        # 图文混合模式
        elif prompt in constants.config.trigger.mixed_only_command:
            conversation_context.switch_renderer("mixed")
            # TODO: export to config file
            return await _respond("已切换至图文混合模式，接下来我的回复将会以图文混合的方式呈现！")

        # 图片模式
        elif prompt in constants.config.trigger.image_only_command:
            conversation_context.switch_renderer("image")
            # TODO: export to config file
            return await _respond("已切换至纯图片模式，接下来我的回复将会以图片呈现！")

        # 文本模式
        elif prompt in constants.config.trigger.text_only_command:
            conversation_context.switch_renderer("text")
            # TODO: export to config file
            return await _respond("已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")

        elif switch_model_search := re.search(constants.config.trigger.switch_model, prompt):
            model_name = switch_model_search[1].strip()
            if model_name in conversation_context.supported_models:
                if not (is_manager or model_name in constants.config.trigger.allowed_models):
                    # TODO: export to config file
                    await _respond(f"不好意思，只有管理员才能切换到 {model_name} 模型！")
                else:
                    await conversation_context.switch_model(model_name)
                    # TODO: export to config file
                    await _respond(f"已切换至 {model_name} 模型，让我们聊天吧！")
            else:
                # TODO: export to config file
                await _respond(
                    f"当前的 AI 不支持切换至 {model_name} 模型，目前仅支持：{conversation_context.supported_models}！")
            return

        # 切换语音
        elif voice_type_search := re.search(constants.config.trigger.switch_voice, prompt):
            new_voice = voice_type_search[1].strip()
            if not conversation_context.tts_engine:
                # TODO: export to config file
                await _respond("未配置文字转语音引擎，无法使用语音功能。")
                return

            if new_voice in ['关闭', "None"]:
                conversation_context.conversation_voice = None
                # TODO: export to config file
                await _respond("已关闭语音功能！")
                return

            conversation_context.conversation_voice = conversation_context.tts_engine.choose_voice(new_voice)
            await _respond(f"已切换至 {conversation_context.conversation_voice.full_name} 语音，让我们继续聊天吧！")
            return

        # 加载预设
        elif preset_search := re.search(constants.config.prompts.command, prompt):
            logger.trace(f"{session_id} - 正在执行预设： {preset_search[1]}")
            await conversation_context.load_preset(preset_search[1])
            _initialization = True
            _no_follow = True

        if not conversation_context.preset:
            # 当前没有预设
            logger.trace(f"{session_id} - 未检测到预设，正在执行默认预设……")
            # 隐式加载不回复预设内容
            await conversation_context.load_preset('catgirl')
            _initialization = True

        async def respond(msg: Optional[MessageChain]):
            """
            Respond method
            """
            if not msg:
                return

            ret = await _respond(msg)
            for m in middlewares:
                await m.on_respond(session_id, prompt, msg)

            if not conversation_context:
                return ret
            # TTS Converting
            if conversation_context.conversation_voice and conversation_context.conversation_voice:
                tasks = []
                for elem in msg:
                    task = asyncio.create_task(
                        conversation_context.tts_engine.speak(elem, conversation_context.conversation_voice))
                    tasks.append(task)
                while tasks:
                    done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for voice_task in done:
                        voice = await voice_task
                        if voice:
                            await _respond(voice)

            return ret

        async with conversation_context as context:
            context.variables['user']['nickname'] = nickname
            context.actions['system/user_message'] = functools.partial(reply, bind=_respond)

            if _initialization:
                await context.init()

            if _no_follow:
                return

            async def request(_session_id, prompt: str, conversation_context, _respond):
                """
                Request method
                """
                await context.input(prompt=prompt)

                # 没有任务那就聊天吧！
                # async for rendered in conversation_context.ask(prompt=prompt, chain=chain, name=nickname):
                #     if rendered:
                #         if not str(rendered).strip():
                #             logger.warning("检测到内容为空的输出，已忽略")
                #             continue
                #         action = lambda session_id, prompt, rendered, respond: respond(rendered)
                #         for m in middlewares:
                #             action = __wrap_respond(action, m)
                #
                #         # 开始处理 handle_response
                #         await action(session_id, prompt, rendered, respond)
                for m in middlewares:
                    await m.handle_respond_completed(session_id, prompt, respond)

            action = request
            for m in middlewares:
                action = __wrap_request(action, m)

            # 开始处理

            await action(session_id, prompt.strip(), conversation_context, respond)
    except DrawingFailedException as e:
        logger.exception(e)
        await _respond(constants.config.response.error_drawing.format(exc=e.__cause__ or '未知'))
    except CommandRefusedException as e:
        await _respond(str(e))
    except openai.error.InvalidRequestError as e:
        await _respond(f"服务器拒绝了您的请求，原因是： {str(e)}")
    except LlmOperationNotSupportedException:
        await _respond("暂不支持此操作，抱歉！")
    except LlmConcurrentMessageException as e:  # Chatbot 账号同时收到多条消息
        await _respond(constants.config.response.error_request_concurrent_error)
    except LlmRateLimitException as e:  # Chatbot 账号限流
        await _respond(constants.config.response.error_request_too_many.format(exc=e))
    except NoAvailableBotException as e:  # 预设不存在
        await _respond(f"当前没有可用的{e}账号，不支持使用此 AI！")
    except BotTypeNotFoundException as e:  # 预设不存在
        respond_msg = f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n"
        # TODO: show supported bot types
        await _respond(respond_msg)
    except PresetNotFoundException:  # 预设不存在
        await _respond("预设不存在，请检查你的输入是否有问题！")
    except (RequestException, SSLError, ProxyError, MaxRetryError, ConnectTimeout, ConnectTimeout,
            httpcore.ReadTimeout, httpx.TimeoutException) as e:  # 网络异常
        await _respond(constants.config.response.error_network_failure.format(exc=e))
    except Exception as e:  # 未处理的异常
        logger.exception(e)
        await _respond(constants.config.response.error_format.format(exc=e))
