import os
from typing import Generator

from adapter.botservice import BotAdapter
from EdgeGPT import Chatbot as EdgeChatbot

from constants import botManager
from exceptions import BotOperationNotSupportedException
import tempfile
import json
from loguru import logger


class BingAdapter(BotAdapter):
    cookieData = None
    cookieFile = None
    count: int = 0

    bot: EdgeChatbot
    """实例"""

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        account = botManager.pick('bing-cookie')
        self.cookieData = []
        for line in account.cookie_content.split("; "):
            key, value = line.split("=", 1)
            self.cookieData.append({"name": key, "value": value})

        self.cookieFile = tempfile.NamedTemporaryFile(mode='w', suffix=".json", encoding='utf8', delete=False)
        self.cookieFile.write(json.dumps(self.cookieData))
        self.cookieFile.close()
        self.bot = EdgeChatbot(self.cookieFile.name)

    def __del__(self):
        if self.cookieFile:
            logger.debug("[Bing] 释放 Cookie 文件……")
            os.remove(self.cookieFile.name)

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.count = 0
        await self.bot.reset()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        remaining_conversations = f'剩余回复数：{self.count} / 8:\n'
        parsed_content = ''
        async for final, response in self.bot.ask_stream(prompt):
            if not final:
                yield remaining_conversations + response
                parsed_content = response
            else:
                try:
                    if parsed_content == '':
                        yield "Bing 已结束本次会话。继续发送消息将重新开启一个新会话。"
                        self.on_reset()
                        return
                    parsed_content = parsed_content + '\n猜你想问：\n'
                    for suggestion in response["item"]["messages"][-1].get("suggestedResponses", []):
                        parsed_content = parsed_content + f"* {suggestion.get('text')}\n"
                    yield remaining_conversations + parsed_content
                except Exception as e:
                    logger.exception(e)

    async def preset_ask(self, role: str, text: str):
        if role.endswith('bot') or role == 'chatgpt':
            logger.debug(f"[预设] 响应：{text}")
            yield text
        else:
            logger.debug(f"[预设] 发送：{text}")
            item = None
            async for item in self.ask(text): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")
            pass  # 不发送 AI 的回应，免得串台
