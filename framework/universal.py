import functools

import asyncio
import re
from typing import Callable, Optional

import httpcore
import httpx
import openai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
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
from framework.request import Request, Response

middlewares = [MiddlewareTimeout(), MiddlewareRatelimit(), MiddlewareBaiduCloud(), MiddlewareConcurrentLock()]


def __wrap_request(next_, middleware):
    """
    Wrapping send messages
    """
    return functools.partial(middleware.handle_request, next=next_)


def __wrap_respond(next_, middleware):
    """
    Wrapping respond messages
    """
    return functools.partial(middleware.handle_respond, next=next_)


async def handle_message(request: Request, response: Response):
    """
    Steps:
    1. 获得消息上下文管理器
    2. 从消息上下文管理器获得当前的消息上下文
    3. 判断是否为指令
    4. 发送给 LLM


    """
    try:
        # 跳过空消息
        if not request.text.strip():
            await response.send(text=constants.config.response.placeholder)
            return

        _initialization = False

        _no_follow = False

        # 跳过要被忽略的消息
        for r in constants.config.trigger.ignore_regex:
            if re.match(r, request.text):
                logger.debug(f"此消息满足正则表达式： {r}，忽略……")
                return

        # 获得消息上下文管理器
        conversation_handler: ConversationHandler = await ConversationHandler.get_handler(request.session_id)

        # TODO: 统一的指令系统

        # 切换 AI 的指令
        if bot_type_search := re.search(constants.config.trigger.switch_command, request.text):
            if not (constants.config.trigger.allow_switching_ai or request.is_manager):
                # TODO: option to modify this
                await response.send(text="不好意思，只有管理员才能切换AI！")
                return
            conversation_handler.current_conversation = (
                await conversation_handler.first_or_create(
                    str(bot_type_search[1].strip())
                )
            )
            # TODO: option to modify this
            await response.send(text=f"已切换至 {bot_type_search[1].strip()} AI，现在开始和我聊天吧！")
            return

        # 指定前缀对话
        if ' ' in request.text and (constants.config.trigger.allow_switching_ai or request.is_manager):
            for ai_type, prefixes in constants.config.trigger.prefix_ai.items():
                for prefix in prefixes:
                    if f'{prefix}' in request.text:
                        request.conversation_context = await conversation_handler.first_or_create(ai_type)
                        request.message = request.message.removeprefix(f'{prefix}')
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
        if not request.conversation_context:
            request.conversation_context = conversation_handler.current_conversation

        # 重置会话
        if request.text in constants.config.trigger.reset_command:
            await request.conversation_context.reset()
            # TODO: export to config file
            return await response.send(text="会话已重置！")

        # 回滚会话
        elif request.text in constants.config.trigger.rollback_command:
            await response.send(
                text=constants.config.response.rollback_success if await request.conversation_context.rollback() else constants.config.response.rollback_fail.format(
                    reset=constants.config.trigger.reset_command))

        # ping
        elif request.text in constants.config.trigger.ping_command:
            # TODO: standardlize this
            # await response.send(text=await get_ping_response(conversation_context))
            return

        # 图文混合模式
        elif request.text in constants.config.trigger.mixed_only_command:
            request.conversation_context.switch_renderer("mixed")
            # TODO: export to config file
            return await response.send(text="已切换至图文混合模式，接下来我的回复将会以图文混合的方式呈现！")

        # 图片模式
        elif request.text in constants.config.trigger.image_only_command:
            request.conversation_context.switch_renderer("image")
            # TODO: export to config file
            return await response.send(text="已切换至纯图片模式，接下来我的回复将会以图片呈现！")

        # 文本模式
        elif request.text in constants.config.trigger.text_only_command:
            request.conversation_context.switch_renderer("text")
            # TODO: export to config file
            return await response.send(text="已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")

        elif switch_model_search := re.search(constants.config.trigger.switch_model, request.text):
            model_name = switch_model_search[1].strip()
            if model_name in request.conversation_context.supported_models:
                if not (request.is_manager or model_name in constants.config.trigger.allowed_models):
                    # TODO: export to config file
                    await response.send(text=f"不好意思，只有管理员才能切换到 {model_name} 模型！")
                else:
                    await request.conversation_context.switch_model(model_name)
                    # TODO: export to config file
                    await response.send(text=f"已切换至 {model_name} 模型，让我们聊天吧！")
            else:
                # TODO: export to config file
                await response.send(
                    text=f"当前的 AI 不支持切换至 {model_name} 模型，目前仅支持：{request.conversation_context.supported_models}！")
            return

        # 切换语音
        elif voice_type_search := re.search(constants.config.trigger.switch_voice, request.text):
            new_voice = voice_type_search[1].strip()
            if not request.conversation_context.tts_engine:
                # TODO: export to config file
                await response.send(text="未配置文字转语音引擎，无法使用语音功能。")
                return

            if new_voice in ['关闭', "None"]:
                request.conversation_context.conversation_voice = None
                # TODO: export to config file
                await response.send(text="已关闭语音功能！")
                return

            request.conversation_context.conversation_voice = request.conversation_context.tts_engine.choose_voice(
                new_voice)
            await response.send(
                text=f"已切换至 {request.conversation_context.conversation_voice.full_name} 语音，让我们继续聊天吧！")
            return

        # 加载预设
        elif preset_search := re.search(constants.config.prompts.command, request.text):
            logger.trace(f"{request.session_id} - 正在执行预设： {preset_search[1]}")
            await request.conversation_context.load_preset(preset_search[1])
            _initialization = True
            _no_follow = True

        if not request.conversation_context.preset:
            # 当前没有预设
            logger.trace(f"{request.session_id} - 未检测到预设，正在执行默认预设……")
            # 隐式加载不回复预设内容
            await request.conversation_context.load_preset('default')
            _initialization = True

        async def _respond_func(chain: MessageChain = None, text: str = None, voice: TTSResponse = None,
                               image: ImageElement = None):
            """
            Respond method
            """
            response.chain = chain
            response.text = text
            response.voice = voice
            response.image = image

            async def _action(_, _response: Response):
                await _response.send(chain=_response.chain, text=_response.text, image=_response.image, voice=_response.voice)

            for _m in middlewares:
                _action = functools.partial(_m.handle_respond, _next=_action)
            ret = await _action(request, response)

            for _m in middlewares:
                await _m.on_respond(request, response)

            return ret

        async with request.conversation_context as context:
            context.variables['user']['nickname'] = request.nickname
            context.actions['system/user_message'] = _respond_func

            if _initialization:
                await context.init()

            if _no_follow:
                return

            async def _request_func(*args, **kwargs):
                """
                Request method
                """
                await context.input(prompt=request.message)
                for _m in middlewares:
                    await _m.handle_respond_completed(request, response)

            action = _request_func
            for m in middlewares:
                action = functools.partial(m.handle_request, _next=action)

            # 开始处理
            await action(request, response)
    except DrawingFailedException as e:
        logger.exception(e)
        await response.send(text=constants.config.response.error_drawing.format(exc=e.__cause__ or '未知'))
    except CommandRefusedException as e:
        await response.send(text=str(e))
    except openai.error.InvalidRequestError as e:
        await response.send(text=f"服务器拒绝了您的请求，原因是： {str(e)}")
    except LlmOperationNotSupportedException:
        await response.send(text="暂不支持此操作，抱歉！")
    except LlmConcurrentMessageException:  # Chatbot 账号同时收到多条消息
        await response.send(text=constants.config.response.error_request_concurrent_error)
    except LlmRateLimitException as e:  # Chatbot 账号限流
        await response.send(text=constants.config.response.error_request_too_many.format(exc=e))
    except NoAvailableBotException as e:  # 预设不存在
        await response.send(text=f"当前没有可用的{e}账号，不支持使用此 AI！")
    except BotTypeNotFoundException as e:  # 预设不存在
        respond_msg = f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n"
        # TODO: show supported bot types
        await response.send(text=respond_msg)
    except PresetNotFoundException:  # 预设不存在
        await response.send(text="预设不存在，请检查你的输入是否有问题！")
    except (RequestException, SSLError, ProxyError, MaxRetryError, ConnectTimeout, ConnectTimeout,
            httpcore.ReadTimeout, httpx.TimeoutException) as e:  # 网络异常
        await response.send(text=constants.config.response.error_network_failure.format(exc=e))
    except Exception as e:  # 未处理的异常
        logger.exception(e)
        await response.send(text=constants.config.response.error_format.format(exc=e))
