from typing import Generator

from adapter.botservice import BotAdapter
from config import OpenAIAPIKey
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import os
from llama_index import (
    GPTTreeIndex,
    GPTKeywordTableIndex,
    GPTSimpleVectorIndex,
    LLMPredictor,
    ServiceContext,
)
from langchain import OpenAI

class LlamaIndexAdapter(BotAdapter):
    api_info: OpenAIAPIKey = None

    def __init__(self, session_id: str = ""):
        self.api_info = botManager.pick('openai-api')
        os.environ['OPENAI_API_KEY'] = self.api_info.api_key
        # self.index = GPTTreeIndex.load_from_disk('./adapter/llama_index/index.json') # 把随地大小便的index.json放在这里
        # self.index = GPTKeywordTableIndex.load_from_disk('./adapter/llama_index/index.json')
        llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.1, model_name="gpt-4", max_tokens=4000))
        service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
        self.index = GPTSimpleVectorIndex.load_from_disk('./adapter/llama_index/github_index.json', service_context=service_context)


    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        return

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:
            yield f"{self.index.query(prompt, verbose=True)}"

        except Exception as e:
            logger.exception(e)
            yield "[llama_index] 出现了些错误"
            await self.on_reset()
            return

    def use_default_preset_ask(self) -> bool:
        """使用默认预设逻辑"""
        return True
