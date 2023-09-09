from enum import Enum
from typing import Generator, Dict, List

import openai
import tiktoken
from loguru import logger

from framework.accounts import account_manager
from framework.llm.llm import Llm
from framework.llm.quora.models import PoeCookieAuth


class BotType(Enum):
    Sage = "gpt-3.5-turbo"
    GPT4 = "chat-gpt-4"
    Claude2 = "claude-2-100k"
    Claude = "claude"
    ChatGPT = "gpt-3.5-turbo"
    Dragonfly = "llama_2_7b"

    @staticmethod
    def parse(bot_name: str):
        tmp_name = bot_name.lower()
        return next(
            (
                bot
                for bot in BotType
                if str(bot.name).lower() == tmp_name
                   or str(bot.value).lower() == tmp_name
                   or f"poe-{str(bot.name).lower()}" == tmp_name
            ),
            None,
        )


def get_token_count(model: str, messages: List[Dict[str, str]]) -> int:
    """
    Get token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        return 0

    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 5
        for key, value in message.items():
            if value:
                num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += 5  # role is always required and always 1 token
    num_tokens += 5  # every reply is primed with <im_start>assistant
    return num_tokens


class PoeAdapter(Llm):
    account: PoeCookieAuth
    messages: List[Dict[str, str]]

    def __init__(self, session_id: str = "unknown", bot_type: BotType = None):
        """获取内部队列"""
        super().__init__(session_id)
        self.__conversation_keep_from = 0
        self.session_id = session_id
        self.model = bot_type.value
        self.account = account_manager.pick("poe-token")
        self.messages = []
        self.max_tokens: int = (
            31000
            if "gpt-4-32k" in self.model
            else 7000
            if "gpt-4" in self.model
            else 15000
            if "gpt-3.5-turbo-16k" in self.model
            else 4000
        )

    async def ask(self, msg: str) -> Generator[str, None, None]:
        """向 AI 发送消息"""
        self.messages.append({"role": "user", "content": msg})
        full_chunk = []
        full_text = ''
        while self.max_tokens - get_token_count(self.model, self.messages) < 0 and \
            len(self.messages) > self.__conversation_keep_from:
            self.messages.pop(self.__conversation_keep_from)
            logger.debug(
                f"清理 token，历史记录遗忘后使用 token 数：{str(get_token_count(self.model, self.messages))}"
            )
        async for chunk in await openai.ChatCompletion.acreate(
            model=self.model,
            messages=self.messages,
            stream=True,
            api_base="https://chatgpt-proxy.lss233.com/poe/v1",
            api_key=self.account.p_b
        ):
            full_chunk.append(chunk.choices[0].delta)
            full_text = ''.join([m.get('content', '') for m in full_chunk])
            yield full_text
        logger.debug(f"[Poe-{self.model}] {self.session_id} - {full_text}")
        self.messages.append({"role": "assistant", "content": full_text})

    async def rollback(self):
        """回滚对话"""
        self.messages = self.messages[:-2 or None]

    async def on_destoryed(self):
        """当会话被重置时，此函数被调用"""
        pass

    async def preset_ask(self, role: str, prompt: str):
        if role.endswith('bot') or role in {'assistant', 'chatgpt'}:
            logger.debug(f"[预设] 响应：{prompt}")
            yield prompt
            role = 'assistant'
        if role not in ['assistant', 'user', 'system']:
            raise ValueError(f"预设文本有误！仅支持设定 assistant、user 或 system 的预设文本，但你写了{role}。")
        self.messages.append({"role": role, "content": prompt})
        self.__conversation_keep_from = len(self.messages)

    @classmethod
    def register(cls):
        account_manager.register_type("poe-token", PoeCookieAuth)
