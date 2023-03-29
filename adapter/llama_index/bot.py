from typing import Generator

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import os
from llama_index import (
    GPTTreeIndex
)


class LlamaIndexAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None

    def __init__(self, session_id: str = ""):
        self.api_info = botManager.pick('openai-api')
        os.environ['OPENAI_API_KEY'] = self.api_info.api_key
        self.index = GPTTreeIndex.load_from_disk('./adapter/llama_index/index.json') # 把随地大小便的index.json放在这里


    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        return

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:
            yield f"{self.index.query(prompt)}"

        except Exception as e:
            logger.exception(e)
            yield "[llama_index] 出现了些错误"
            await self.on_reset()
            return

    def use_default_preset_ask(self) -> bool:
        """使用默认预设逻辑"""
        return True
