import json
from io import BytesIO
from typing import Generator, Union, List

import aiohttp
import re
import asyncio
from PIL import Image

from constants import config
from adapter.botservice import BotAdapter
from EdgeGPT.EdgeGPT import Chatbot as EdgeChatbot, ConversationStyle, NotAllowedToAccess
from contextlib import suppress

from constants import botManager
from drawing import DrawingAPI
from exceptions import BotOperationNotSupportedException
from loguru import logger
from EdgeGPT.ImageGen import ImageGenAsync
from graia.ariadne.message.element import Image as GraiaImage

image_pattern = r"!\[.*\]\((.*)\)"


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
        try:
            self.bot = EdgeChatbot(cookies=self.cookieData, proxy=account.proxy)
        except NotAllowedToAccess as e:
            raise Exception("Bing 账号 Cookie 已过期，请联系管理员更新！") from e

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.count = 0
        await self.bot.reset()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        parsed_content = ''
        image_urls = []
        try:
            async for final, response in self.bot.ask_stream(prompt=prompt,
                                                             conversation_style=self.conversation_style,
                                                             wss_link=config.bing.wss_link,
                                                             locale="zh-cn"):
                if not response:
                    continue

                if final:
                    # 最后一条消息
                    max_messages = config.bing.max_messages
                    with suppress(KeyError):
                        max_messages = response["item"]["throttling"]["maxNumUserMessagesInConversation"]

                    with suppress(KeyError):
                        raw_text = response["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
                        image_urls = re.findall(image_pattern, raw_text)

                    remaining_conversations = f'\n剩余回复数：{self.count} / {max_messages} ' \
                        if config.bing.show_remaining_count else ''

                    if len(response["item"].get('messages', [])) > 1 and config.bing.show_suggestions:
                        suggestions = response["item"]["messages"][-1].get("suggestedResponses", [])
                        if len(suggestions) > 0:
                            parsed_content = parsed_content + '\n猜你想问：  \n'
                            for suggestion in suggestions:
                                parsed_content = f"{parsed_content}* {suggestion.get('text')}  \n"

                    parsed_content = parsed_content + remaining_conversations

                    if parsed_content == remaining_conversations:  # No content
                        yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
                        await self.on_reset()
                        return
                else:
                    # 生成中的消息
                    parsed_content = re.sub(r"Searching the web for:(.*)\n", "", response)
                    parsed_content = re.sub(r"```json(.*)```", "", parsed_content,flags=re.DOTALL)
                    parsed_content = re.sub(r"Generating answers for you...", "", parsed_content)
                    if config.bing.show_references:
                        parsed_content = re.sub(r"\[(\d+)\]: ", r"\1: ", parsed_content)
                    else:
                        parsed_content = re.sub(r"(\[\d+\]\: .+)+", "", parsed_content)
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
                    all_cookies=self.bot.chat_hub.cookies,
                    quiet=True
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
        if role.endswith('bot') or role in {'assistant', 'bing'}:
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")

