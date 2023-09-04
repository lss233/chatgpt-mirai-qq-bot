import asyncio
import time
from enum import Enum
from typing import Generator

from loguru import logger
from poe import Client as PoeClient

from adapter.botservice import BotAdapter
from constants import botManager


class PoeBot(Enum):
    """Poe 支持的机器人：{'capybara': 'Assistant', 'a2': 'Claude-instant', 'beaver': 'GPT-4', 'chinchilla': 'ChatGPT',
    'llama_2_7b_chat': 'Llama-2-7b', 'a2_100k': 'Claude-instant-100k', 'llama_2_13b_chat': 'Llama-2-13b', 'agouti': 'ChatGPT-16k', 
    'vizcacha': 'GPT-4-32k', 'acouchy': 'Google-PaLM', 'llama_2_70b_chat':'Llama-2-70b', 'a2_2': 'Claude-2-100k'} """
    Sage = "capybara"
    GPT4 = "beaver"
    GPT432k = "vizcacha"
    Claude2 = "a2_2"
    Claude = "a2"
    Claude100k = "a2_100k"
    ChatGPT = "chinchilla"
    ChatGPT16k = "agouti"
    Llama2 = "llama_2_70b_chat"
    PaLM = "acouchy"

    @staticmethod
    def parse(bot_name: str):
        tmp_name = bot_name.lower()
        return next(
            (
                bot
                for bot in PoeBot
                if str(bot.name).lower() == tmp_name
                or str(bot.value).lower() == tmp_name
                or f"poe-{str(bot.name).lower()}" == tmp_name
                or f"poe-{str(bot.value).lower()}" == tmp_name 
            ),
            None,
        )


class PoeClientWrapper:
    def __init__(self, client_id: int, client: PoeClient, p_b: str):
        self.client_id = client_id
        self.client = client
        self.p_b = p_b
        self.last_ask_time = None


class PoeAdapter(BotAdapter):

    def __init__(self, session_id: str = "unknown", poe_bot: PoeBot = None):
        """获取内部队列"""
        super().__init__(session_id)
        self.session_id = session_id
        self.poe_bot = poe_bot or PoeBot.ChatGPT
        self.poe_client: PoeClientWrapper = botManager.pick("poe-web")
        self.process_retry = 0

    async def ask(self, msg: str) -> Generator[str, None, None]:
        self.check_and_reset_client()
        try:
            """向 AI 发送消息"""
            final_resp = None
            while None in self.poe_client.client.active_messages.values():
                await asyncio.sleep(0.01)
            for final_resp in self.poe_client.client.send_message(chatbot=self.poe_bot.value, message=msg):
                yield final_resp["text"]
            if final_resp is None:
                raise Exception("Poe 在返回结果时出现了错误")
            yield final_resp["text"]
            self.process_retry = 0
            self.poe_client.last_ask_time = time.time()
        except Exception as e:
            logger.warning(f"Poe connection error {str(e)}")
            if self.process_retry > 3:
                raise e
            new_poe_client = botManager.reset_bot(self.poe_client)
            self.poe_client = new_poe_client
            self.process_retry += 1
            async for resp in self.ask(msg):
                yield resp

    def check_and_reset_client(self):
        current_time = time.time()
        last_ask_time = self.poe_client.last_ask_time
        if last_ask_time and current_time - last_ask_time > 3600:
            new_poe_client = botManager.reset_bot(self.poe_client)
            self.poe_client = new_poe_client

    async def rollback(self):
        """回滚对话"""
        try:
            self.poe_client.client.purge_conversation(self.poe_bot.value, 2)
            self.process_retry = 0
        except Exception as e:
            logger.warning(f"Poe connection error {str(e)}")
            if self.process_retry > 3:
                raise e
            new_poe_client = botManager.reset_bot(self.poe_client)
            self.poe_client = new_poe_client
            self.process_retry += 1
            await self.rollback()

    async def on_reset(self):
        """当会话被重置时，此函数被调用"""
        try:
            self.poe_client.client.send_chat_break(self.poe_bot.value)
            self.process_retry = 0
        except Exception as e:
            logger.warning(f"Poe connection error {str(e)}")
            if self.process_retry > 3:
                raise e
            new_poe_client = botManager.reset_bot(self.poe_client)
            self.poe_client = new_poe_client
            self.process_retry += 1
            await self.on_reset()
