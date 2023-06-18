import json
import aiohttp
from loguru import logger
from config import Config
from typing import Callable
from graia.ariadne.message.element import Image
from middlewares.middleware import Middleware

config = Config.load_config()


class OpenAIModeration():
    def __init__(self):
        self.openai_api = config.openai_moderation.openai_api_key

    async def get_conclusion(self, text: str):
        moderation_url = f"https://api.openai.com/v1/moderations"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            "Authorization": "Bearer " + self.openai_api
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(moderation_url, headers=headers, data={'input': text},
                                    proxy=config.openai_moderation.proxy) as response:
                response.raise_for_status()
                response_dict = await response.json()

        return response_dict


class MiddlewareOpenAIModeration(Middleware):
    def __init__(self):
        self.openai_moderation = OpenAIModeration()

    async def handle_respond(self, session_id: str, prompt: str, rendered: str, respond: Callable, action: Callable):
        if not config.openai_moderation.check:
            return await action(session_id, prompt, rendered, respond)
        if isinstance(rendered, Image):
            return await action(session_id, prompt, rendered, respond)

        should_pass = False

        try:
            response_dict = await self.openai_moderation.get_conclusion(rendered)

            # 处理审核结果
            conclusion = response_dict['results'][0]['flagged']
            # 如果未被标记
            if not conclusion:
                logger.success(f"[OpenAI文本审核] 判定结果：合规")
                should_pass = True
            else:
                # 获取被标记原因
                categories = response_dict['results'][0]['categories']
                reasons = []
                if isinstance(categories, dict):
                    for reason, value in categories.items():
                        if value:
                            reasons.append(reason)

                msg = ','.join(reasons)
                logger.error(f"[OpenAI文本审核] 判定结果：不合规")
                conclusion = f"{config.openai_moderation.prompt_message}\n原因：{msg}"
                return await action(session_id, prompt, conclusion, respond)

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error occurred: {e}")

            await respond("[OpenAI文本审核] 判定出错\n以下是原消息：")
            should_pass = True

        except json.JSONDecodeError as e:
            logger.error(f"[OpenAI文本审核] JSON decode error occurred: {e}")
        except StopIteration as e:
            logger.error(f"[OpenAI文本审核] StopIteration exception occurred: {e}")
        if should_pass:
            return await action(session_id, prompt, rendered, respond)
