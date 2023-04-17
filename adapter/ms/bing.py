import json
from typing import Generator, Union, List

import aiohttp
import asyncio
from constants import config
from adapter.botservice import BotAdapter
from EdgeGPT import Chatbot as EdgeChatbot, ConversationStyle

from constants import botManager
from drawing import DrawingAPI
from exceptions import BotOperationNotSupportedException
from loguru import logger
import re
from ImageGen import ImageGenAsync
from graia.ariadne.message.element import Image as GraiaImage

class BingAdapter(BotAdapter, DrawingAPI):
    cookieData = None
    count: int = 0

    conversation_style: ConversationStyle = None

    bot: EdgeChatbot
    """实例"""

    def __init__(self, session_id: str = "unknown", conversation_style: ConversationStyle = ConversationStyle.creative):
        super().__init__(session_id)
        self.session_id = session_id
        self.conversation_style = conversation_style
        account = botManager.pick('bing-cookie')
        self.cookieData = []
        if account.cookie_content.strip().startswith('['):
            self.cookieData = json.loads(account.cookie_content)
        else:
            for line in account.cookie_content.split("; "):
                name, value = line.split("=", 1)
                self.cookieData.append({"name": name, "value": value})

        self.bot = EdgeChatbot(cookies=self.cookieData, proxy=account.proxy)

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.count = 0
        await self.bot.reset()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        parsed_content = ''
        try:
            async for final, response in self.bot.ask_stream(prompt=prompt,
                                                             conversation_style=self.conversation_style,
                                                             wss_link=config.bing.wss_link):
                if not final:
                    response = re.sub(r"\[\^\d+\^\]", "", response)
                    if config.bing.show_references:
                        response = re.sub(r"\[(\d+)\]: ", r"\1: ", response)
                    else:
                        response = re.sub(r"(\[\d+\]\: .+)+", "", response)
                    parsed_content = response

                else:
                    try:
                        max_messages = response["item"]["throttling"]["maxNumUserMessagesInConversation"]
                    except Exception:
                        max_messages = config.bing.max_messages
                    if config.bing.show_remaining_count:
                        remaining_conversations = f'\n剩余回复数：{self.count} / {max_messages} '
                    else:
                        remaining_conversations = ''
                    if len(response["item"].get('messages', [])) > 1 and config.bing.show_suggestions:
                        suggestions = response["item"]["messages"][-1].get("suggestedResponses", [])
                        if len(suggestions) > 0:
                            parsed_content = parsed_content + '\n猜你想问：  \n'
                            for suggestion in suggestions:
                                parsed_content = f"{parsed_content}* {suggestion.get('text')}  \n"
                        yield parsed_content
                    parsed_content = parsed_content + remaining_conversations
                    # not final的parsed_content已经yield走了，只能在末尾加剩余回复数，或者改用EdgeGPT自己封装的ask之后再正则替换
                    if parsed_content == remaining_conversations:  # No content
                        yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
                        await self.on_reset()
                        return

                yield parsed_content
            logger.debug(f"[Bing AI 响应] {parsed_content}")
        except (asyncio.exceptions.TimeoutError, asyncio.exceptions.CancelledError) as e:
            raise e
        except Exception as e:
            logger.exception(e)
            yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
            await self.on_reset()
            return

    async def text_to_img(self, prompt: str):
        logger.debug(f"[Bing Image] Prompt: {prompt}")

        async with ImageGenAsync(
                next((cookie['value'] for cookie in self.bot.cookies if cookie['name'] == '_U'), None),
                False
        ) as image_generator:
            images = await image_generator.get_images(prompt)

            logger.debug(f"[Bing Image] Response: {images}")
            tasks = [asyncio.create_task(self.__download_image(image)) for image in images]
            return await asyncio.gather(*tasks)

    async def img_to_img(self, init_images: List[GraiaImage], prompt=''):
        return await self.text_to_img(prompt)

    async def __download_image(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=self.bot.proxy) as resp:
                if resp.status == 200:
                    return GraiaImage(data_bytes=await resp.read())

    async def preset_ask(self, role: str, text: str):
        yield None  # Bing 不使用预设功能
