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

from command import CommandHandler
from constants import botManager, BotPlatform
from constants import config
from conversation import ConversationHandler
from exceptions import PresetNotFoundException, BotRatelimitException, ConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, BotOperationNotSupportedException, CommandRefusedException, \
    DrawingFailedException

from utils.text_to_speech import get_tts_voice, VoiceType
from middlewares.middlewares_loader import load_middlewares

command_handler = CommandHandler()

middlewares = load_middlewares()


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
            conversation_context = conversation_handler.current_conversation

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

        task = [None]

        if not conversation_context:
            conversation_context = conversation_handler.current_conversation

        # 命令处理
        if await command_handler.handle_command(prompt, session_id, conversation_context, conversation_handler, respond,
                                                is_manager, task):
            return

        # 没有任务那就聊天吧！
        if not task[0]:
            task[0] = conversation_context.ask(prompt=prompt, chain=chain, name=nickname)
        async for rendered in task[0]:
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
