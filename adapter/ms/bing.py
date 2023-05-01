import json
import re
from contextlib import suppress
from typing import Generator, List

import aiohttp
import asyncio
import httpx
from EdgeGPT import Chatbot as EdgeChatbot, ConversationStyle, NotAllowedToAccess
from ImageGen import ImageGenAsync
from graia.ariadne.message.element import Image as GraiaImage
from loguru import logger

from accounts import account_manager, AccountInfoBaseModel
from adapter.botservice import BotAdapter
import constants
from drawing import DrawingAPI
from exceptions import BotOperationNotSupportedException

image_pattern = r"!\[.*\]\((.*)\)"


class BingCookieAuth(AccountInfoBaseModel):
    cookie_content: str
    """Bing 的 Cookie"""

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient(
                trust_env=True,
                headers={
                    "Cookie": self.cookie_content,
                    "sec-ch-ua": r'"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.64'
                }
        ) as client:
            response = await client.get(f"{constants.config.bing.bing_endpoint}")
            return "Success" in response.text


class BingAdapter(BotAdapter, DrawingAPI):
    cookieData = None
    count: int = 0

    conversation_style: ConversationStyle = None

    bot: EdgeChatbot
    """底层实现"""

    def __init__(self, session_id: str = "unknown", conversation_style: ConversationStyle = ConversationStyle.creative):
        super().__init__(session_id)
        self.session_id = session_id
        self.conversation_style = conversation_style
        account = account_manager.pick('bing-cookie')
        self.cookieData = json.loads(account.cookie_content)
        self.bot = EdgeChatbot(cookies=self.cookieData, proxy=account.proxy)

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_destoryed(self):
        ...

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        parsed_content = ''
        image_urls = []
        try:
            async for final, response in self.bot.ask_stream(prompt=prompt,
                                                             conversation_style=self.conversation_style,
                                                             wss_link=constants.config.bing.wss_link):
                if not response:
                    continue

                if final:
                    # 最后一条消息
                    max_messages = constants.config.bing.max_messages
                    with suppress(KeyError):
                        max_messages = response["item"]["throttling"]["maxNumUserMessagesInConversation"]

                    with suppress(KeyError):
                        raw_text = response["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
                        image_urls = re.findall(image_pattern, raw_text)

                    remaining_conversations = f'\n剩余回复数：{self.count} / {max_messages} ' \
                        if constants.config.bing.show_remaining_count else ''

                    if len(response["item"].get('messages', [])) > 1 and constants.config.bing.show_suggestions:
                        suggestions = response["item"]["messages"][-1].get("suggestedResponses", [])
                        if len(suggestions) > 0:
                            parsed_content = parsed_content + '\n猜你想问：  \n'
                            for suggestion in suggestions:
                                parsed_content = f"{parsed_content}* {suggestion.get('text')}  \n"

                    parsed_content = parsed_content + remaining_conversations

                    if parsed_content == remaining_conversations:  # No content
                        yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
                        self.count = 0
                        await self.bot.reset()
                        return
                else:
                    # 生成中的消息
                    parsed_content = re.sub(r"\[\^\d+\^]", "", response)
                    if constants.config.bing.show_references:
                        parsed_content = re.sub(r"\[(\d+)]: ", r"\1: ", parsed_content)
                    else:
                        parsed_content = re.sub(r"(\[\d+]: .+)+", "", parsed_content)
                    parts = re.split(image_pattern, parsed_content)
                    # 图片单独保存
                    parsed_content = parts[0]

                    if len(parts) > 2:
                        parsed_content = parsed_content + parts[-1]

                yield parsed_content
            logger.debug(f"[Bing AI 响应] {parsed_content}")
            image_tasks = [
                asyncio.create_task(self.__download_image(url))
                for url in image_urls
            ]
            for image in await asyncio.gather(*image_tasks):
                yield image
        except (asyncio.exceptions.TimeoutError, asyncio.exceptions.CancelledError) as e:
            raise e
        except NotAllowedToAccess:
            yield "出现错误：机器人的 Bing Cookie 可能已过期，或者机器人当前使用的 IP 无法使用 Bing AI。"
            return
        except Exception as e:
            if str(e) == 'Redirect failed':
                yield '画图失败：Redirect failed'
                return
            raise e

    async def text_to_img(self, prompt: str):
        logger.debug(f"[Bing Image] Prompt: {prompt}")
        try:
            async with ImageGenAsync(
                    next((cookie['value'] for cookie in self.bot.cookies if cookie['name'] == '_U'), None),
                    False
            ) as image_generator:
                images = await image_generator.get_images(prompt)

                logger.debug(f"[Bing Image] Response: {images}")
                tasks = [asyncio.create_task(self.__download_image(image)) for image in images]
                return await asyncio.gather(*tasks)
        except Exception as e:
            if str(e) == 'Redirect failed':
                raise Exception('画图失败：Redirect failed') from e
            raise e

    async def img_to_img(self, init_images: List[GraiaImage], prompt=''):
        return await self.text_to_img(prompt)

    async def __download_image(self, url) -> GraiaImage:
        logger.debug(f"[Bing AI] 下载图片：{url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=self.bot.proxy) as resp:
                resp.raise_for_status()
                logger.debug(f"[Bing AI] 下载完成：{resp.content_type} {url}")
                return GraiaImage(data_bytes=await resp.read())

    async def preset_ask(self, role: str, text: str):
        yield None  # Bing 不使用预设功能

    @classmethod
    def register(cls):
        account_manager.register_type("bing", BingCookieAuth)
