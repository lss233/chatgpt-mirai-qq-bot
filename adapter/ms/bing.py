import asyncio
from typing import Generator

from adapter.botservice import BotAdapter
from EdgeGPT import Chatbot as EdgeChatbot, ConversationStyle

from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import re


class BingAdapter(BotAdapter):
    cookieData = None
    count: int = 0

    conversation_style: ConversationStyle = None

    bot: EdgeChatbot
    """实例"""

    def __init__(self, session_id: str = "unknown", conversation_style: ConversationStyle = ConversationStyle.creative):
        self.session_id = session_id
        self.conversation_style = conversation_style
        account = botManager.pick('bing-cookie')
        self.cookieData = []
        for line in account.cookie_content.split("; "):
            name, value = line.split("=", 1)
            self.cookieData.append({"name": name, "value": value})

        self.bot = EdgeChatbot(cookies=self.cookieData)

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.count = 0
        await self.bot.reset()
        self.lock = asyncio.Lock()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        remaining_conversations = f'剩余回复数：{self.count} / 8:\n'
        parsed_content = ''
        try:
            async for final, response in self.bot.ask_stream(prompt=prompt,
                                                             conversation_style=self.conversation_style):
                if not final:
                    response = re.sub(r"\[\^\d+\^\]", "", response)
                    yield remaining_conversations + response
                    parsed_content = response
                else:
                    suggestions = response["item"]["messages"][-1].get("suggestedResponses", [])
                    if len(suggestions) > 0:
                        parsed_content = parsed_content + '\n猜你想问：\n'
                        for suggestion in suggestions:
                            parsed_content = parsed_content + f"* {suggestion.get('text')}\n"
                    if parsed_content == '':
                        yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
                        await self.on_reset()
                        return
                    yield remaining_conversations + parsed_content
        except Exception as e:
            logger.exception(e)
            yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
            await self.on_reset()
            return

    async def preset_ask(self, role: str, text: str):
        # 不会给 Bing 提供预设
        yield None
