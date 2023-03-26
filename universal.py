import re
from typing import Callable

import openai
from graia.ariadne.message.chain import MessageChain
from httpx import HTTPStatusError, ConnectTimeout
from loguru import logger
from requests.exceptions import SSLError, ProxyError, RequestException
from urllib3.exceptions import MaxRetryError

from constants import config
from conversation import ConversationHandler
from exceptions import PresetNotFoundException, BotRatelimitException, ConcurrentMessageException, \
    BotTypeNotFoundException, NoAvailableBotException, BotOperationNotSupportedException, CommandRefusedException
from middlewares.baiducloud import MiddlewareBaiduCloud
from middlewares.concurrentlock import MiddlewareConcurrentLock
from middlewares.ratelimit import MiddlewareRatelimit
from middlewares.timeout import MiddlewareTimeout

middlewares = [MiddlewareTimeout(), MiddlewareRatelimit(), MiddlewareBaiduCloud(), MiddlewareConcurrentLock()]


async def handle_message(_respond: Callable, session_id: str, message: str, chain: MessageChain = MessageChain("Unsupported"), is_manager: bool = False, nickname: str = '某人'):
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
    if ' ' in message:
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
        return ret

    async def request(_session_id, prompt: str, conversation_context, _respond):
        try:
            task = None

            # 不带前缀 - 正常初始化会话
            if bot_type_search := re.search(config.trigger.switch_command, prompt):
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
                    await respond(f"当前的 AI 不支持切换至 {model_name} 模型，目前仅支持：{conversation_context.supported_models}！")
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
            await respond(
                f"AI类型{e}不存在，请检查你的输入是否有问题！目前仅支持：\n"
                f"* chatgpt-web - OpenAI ChatGPT 网页版\n"
                f"* chatgpt-api - OpenAI ChatGPT API版\n"
                f"* bing-c - 微软 New Bing (创造力)\n"
                f"* bing-b - 微软 New Bing (平衡)\n"
                f"* bing-p - 微软 New Bing (精确)\n"
                f"* bard   - Google Bard\n"
                f"* yiyan  - 百度 文心一言\n"
            )
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
