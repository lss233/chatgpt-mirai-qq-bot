import os
import re
from typing import Callable

import openai
from tempfile import NamedTemporaryFile
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Voice
from httpx import HTTPStatusError, ConnectTimeout
from loguru import logger
from requests.exceptions import SSLError, ProxyError, RequestException
from urllib3.exceptions import MaxRetryError

from constants import config
from constants import botManager

from conversation import ConversationHandler
from exceptions import PresetNotFoundException, BotRatelimitException, ConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, BotOperationNotSupportedException, CommandRefusedException
from middlewares.baiducloud import MiddlewareBaiduCloud
from middlewares.concurrentlock import MiddlewareConcurrentLock
from middlewares.ratelimit import MiddlewareRatelimit
from middlewares.timeout import MiddlewareTimeout

from utils.azure_tts import synthesize_speech

middlewares = [MiddlewareTimeout(), MiddlewareRatelimit(), MiddlewareBaiduCloud(), MiddlewareConcurrentLock()]


async def handle_message(_respond: Callable, session_id: str, message: str,
                         chain: MessageChain = MessageChain("Unsupported"), is_manager: bool = False,
                         nickname: str = '某人'):
    """正常聊天"""
    if not message.strip():
        return config.response.placeholder

    for r in config.trigger.ignore_regex:
        if re.match(r, message):
            logger.debug(f"此消息满足正则表达式： {r}，忽略……")
            return

    # 此处为会话不存在时可以执行的指令
    conversation_handler = await ConversationHandler.get_handler(session_id)
    conversation_context = None
    # 指定前缀对话
    if ' ' in message and (config.trigger.allow_switching_ai or is_manager):
        for ai_type, prefixes in config.trigger.prefix_ai.items():
            for prefix in prefixes:
                if prefix + ' ' in message:
                    conversation_context = await conversation_handler.first_or_create(ai_type)
                    message = message.removeprefix(prefix + ' ')
                    break
            else:
                # Continue if the inner loop wasn't broken.
                continue
            # Inner loop was broken, break the outer.
            break
    if not conversation_handler.current_conversation:
        conversation_handler.current_conversation = await conversation_handler.create(
            config.response.default_ai)

    def wrap_request(n, m):
        async def call(session_id, message, conversation_context, respond):
            await m.handle_request(session_id, message, respond, conversation_context, n)

        return call

    def wrap_respond(n, m):
        async def call(session_id, message, rendered, respond):
            await m.handle_respond(session_id, message, rendered, respond, n)

        return call

    async def respond(msg: str):
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
        # TTS Converting
        if conversation_context.conversation_voice and isinstance(msg, MessageChain):
            for elem in msg:
                if isinstance(elem, Plain) and str(elem):
                    output_file = NamedTemporaryFile(mode='w+b', suffix='.wav', delete=False)
                    output_file.close()
                    if await synthesize_speech(
                            str(elem),
                            output_file.name,
                            conversation_context.conversation_voice
                    ):
                        await _respond(Voice(path=output_file.name))
                    try:
                        os.unlink(output_file.name)
                    except:
                        pass
        return ret

    async def request(_session_id, prompt: str, conversation_context, _respond):
        try:
            task = None

            # 不带前缀 - 正常初始化会话
            if bot_type_search := re.search(config.trigger.switch_command, prompt):
                if not (config.trigger.allow_switching_ai or is_manager):
                    await respond(f"不好意思，只有管理员才能切换AI！")
                    return
                conversation_handler.current_conversation = await conversation_handler.create(
                    bot_type_search.group(1).strip())
                await respond(f"已切换至 {bot_type_search.group(1).strip()} AI，现在开始和我聊天吧！")
                return
            # 最终要选择的对话上下文
            if not conversation_context:
                conversation_context = conversation_handler.current_conversation
            # 此处为会话存在后可执行的指令

            # 重置会话
            if prompt in config.trigger.reset_command:
                task = conversation_context.reset()

            # 回滚会话
            elif prompt in config.trigger.rollback_command:
                task = conversation_context.rollback()

            elif voice_type_search := re.search(config.trigger.switch_voice, prompt):
                if config.azure.tts_speech_key:
                    conversation_context.conversation_voice = voice_type_search.group(1).strip()
                    await respond(
                        f"已切换至 {conversation_context.conversation_voice} 语音！详情参考： "
                        f"https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=tts#neural-voices")
                else:
                    await respond(f"未配置 Azure TTS 账户，无法切换语音！")
                return

            elif prompt in config.trigger.mixed_only_command:
                conversation_context.switch_renderer("mixed")
                await respond(f"已切换至图文混合模式，接下来我的回复将会以图文混合的方式呈现！")
                return

            elif prompt in config.trigger.image_only_command:
                conversation_context.switch_renderer("image")
                await respond(f"已切换至纯图片模式，接下来我的回复将会以图片呈现！")
                return

            elif prompt in config.trigger.text_only_command:
                conversation_context.switch_renderer("text")
                await respond(f"已切换至纯文字模式，接下来我的回复将会以文字呈现（被吞除外）！")
                return

            elif switch_model_search := re.search(config.trigger.switch_model, prompt):
                model_name = switch_model_search.group(1).strip()
                if model_name in conversation_context.supported_models:
                    if not (is_manager or model_name in config.trigger.allowed_models):
                        await respond(f"不好意思，只有管理员才能切换到 {model_name} 模型！")
                    else:
                        await conversation_context.switch_model(model_name)
                        await respond(f"已切换至 {model_name} 模型，让我们聊天吧！")
                else:
                    await respond(
                        f"当前的 AI 不支持切换至 {model_name} 模型，目前仅支持：{conversation_context.supported_models}！")
                return

            # 加载预设
            if preset_search := re.search(config.presets.command, prompt):
                logger.trace(f"{session_id} - 正在执行预设： {preset_search.group(1)}")
                async for _ in conversation_context.reset(): ...
                task = conversation_context.load_preset(preset_search.group(1))
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
                    if str(rendered).strip() == '':
                        logger.warning("检测到内容为空的输出，已忽略")
                        continue
                    action = lambda session_id, prompt, rendered, respond: respond(rendered)
                    for m in middlewares:
                        action = wrap_respond(action, m)

                    # 开始处理 handle_response
                    await action(session_id, prompt, rendered, respond)
            for m in middlewares:
                await m.handle_respond_completed(session_id, prompt, respond)
        except CommandRefusedException as e:
            await respond(str(e))
        except openai.error.InvalidRequestError as e:
            await respond("服务器拒绝了您的请求，原因是" + str(e))
        except BotOperationNotSupportedException:
            await respond("暂不支持此操作，抱歉！")
        except ConcurrentMessageException as e:  # Chatbot 账号同时收到多条消息
            await respond(config.response.error_request_concurrent_error)
        except (BotRatelimitException, HTTPStatusError) as e:  # Chatbot 账号限流
            await respond(config.response.error_request_too_many.format(exc=e))
        except NoAvailableBotException as e:  # 预设不存在
            await respond(f"当前没有可用的{e}账号，不支持使用此 AI！")
        except BotTypeNotFoundException as e:  # 预设不存在
            respond_msg = f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n"
            if len(botManager.bots['chatgpt-web']) > 0:
                respond_msg += "* chatgpt-web - OpenAI ChatGPT 网页版\n"
            if len(botManager.bots['openai-api']) > 0:
                respond_msg += "* chatgpt-api - OpenAI ChatGPT API版\n"
            if len(botManager.bots['bing-cookie']) > 0:
                respond_msg += "* bing-c - 微软 New Bing (创造力)\n"
                respond_msg += "* bing-b - 微软 New Bing (平衡)\n"
                respond_msg += "* bing-p - 微软 New Bing (精确)\n"
            if len(botManager.bots['bard-cookie']) > 0:
                respond_msg += "* bard   - Google Bard\n"
            if len(botManager.bots['yiyan-cookie']) > 0:
                respond_msg += "* yiyan  - 百度 文心一言\n"
            if len(botManager.bots['chatglm-api']) > 0:
                respond_msg += "* chatglm-api - 清华 ChatGLM-6B (本地)\n"
            if len(botManager.bots['poe-web']) > 0:
                respond_msg += "* sage   - POE Sage 模型\n"
                respond_msg += "* calude - POE Calude 模型\n"
                respond_msg += "* chinchilla - POE ChatGPT 模型\n"
            await respond(respond_msg)
        except PresetNotFoundException:  # 预设不存在
            await respond("预设不存在，请检查你的输入是否有问题！")
        except (RequestException, SSLError, ProxyError, MaxRetryError, ConnectTimeout, ConnectTimeout) as e:  # 网络异常
            await respond(config.response.error_network_failure.format(exc=e))
        except Exception as e:  # 未处理的异常
            logger.exception(e)
            await respond(config.response.error_format.format(exc=e))

    action = request
    for m in middlewares:
        action = wrap_request(action, m)

    # 开始处理
    await action(session_id, message.strip(), conversation_context, respond)
