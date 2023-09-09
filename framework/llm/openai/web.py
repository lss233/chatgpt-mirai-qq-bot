import datetime
from typing import Generator, Union

import revChatGPT.V1 as ChatGPTV1
from loguru import logger
from revChatGPT.typings import Error as V1Error

from framework.accounts import account_manager
from framework.chatbot.chatgpt import ChatGPTBrowserChatbot
from framework.exceptions import LlmRateLimitException, LlmConcurrentMessageException
from framework.llm.llm import Llm
from framework.llm.openai.models import OpenAIAccessTokenAuth, OpenAIWebAuthBaseModel


class ChatGPTWebAdapter(Llm):
    conversation_id: str
    """会话 ID"""

    parent_id: str
    """上文 ID"""

    conversation_id_prev_queue = []
    parent_id_prev_queue = []

    account: OpenAIWebAuthBaseModel

    bot: ChatGPTBrowserChatbot = None
    """底层实现"""

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.account = account_manager.pick("chatgpt-web")
        self.bot = self.account.get_client()
        self.conversation_id = None
        self.parent_id = None
        super().__init__()
        self.current_model = self.account.model or (
            'text-davinci-002-render-paid'
            if self.account.paid else
            'text-davinci-002-render-sha'
        )
        self.supported_models = ['text-davinci-002-render-sha']
        if self.account.paid:
            self.supported_models.append('text-davinci-002-render-paid')
            self.supported_models.append('gpt-4')
            self.supported_models.append('gpt-4-mobile')
            self.supported_models.append('gpt-4-browsing')
            self.supported_models.append('gpt-4-plugins')

    async def switch_model(self, model_name):
        if (
                self.account.auto_remove_old_conversations
                and self.conversation_id is not None
        ):
            await self.bot.delete_conversation(self.conversation_id)
        self.conversation_id = None
        self.parent_id = None
        self.current_model = model_name
        await self.on_destoryed()

    async def rollback(self):
        if len(self.parent_id_prev_queue) <= 0:
            return False
        self.conversation_id = self.conversation_id_prev_queue.pop()
        self.parent_id = self.parent_id_prev_queue.pop()
        return True

    async def on_destoryed(self):
        try:
            if (
                    self.account.auto_remove_old_conversations
                    and self.conversation_id is not None
            ):
                await self.bot.delete_conversation(self.conversation_id)
        except Exception:
            logger.warning("删除会话记录失败。")
        self.conversation_id = None
        self.parent_id = None
        self.bot = account_manager.pick('chatgpt-web')

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:
            last_response = None
            async for resp in self.bot.ask(prompt, self.conversation_id, self.parent_id, model=self.current_model):
                last_response = resp
                if self.conversation_id:
                    self.conversation_id_prev_queue.append(self.conversation_id)
                if self.parent_id:
                    self.parent_id_prev_queue.append(self.parent_id)

                # 初始化会话 ID
                if not self.conversation_id:
                    self.conversation_id = resp["conversation_id"]
                    if self.account.title_pattern:
                        await self.bot.rename_conversation(self.conversation_id, self.account.title_pattern
                                                           .format(session_id=self.session_id))

                # 确保是当前的会话，才更新 parent_id
                if self.conversation_id == resp["conversation_id"]:
                    self.parent_id = resp["parent_id"]

                yield resp["message"]
            if last_response:
                logger.debug(f"[ChatGPT-Web] {last_response['conversation_id']} - {last_response['message']}")
        except V1Error as e:
            if e.code == 2 or e.code == 429:
                current_time = datetime.datetime.now()
                self.bot.refresh_accessed_at()
                logger.debug(f"[ChatGPT-Web] accessed at: {str(self.bot.accessed_at)}")
                first_accessed_at = self.bot.accessed_at[0] if len(self.bot.accessed_at) > 0 \
                    else current_time - datetime.timedelta(hours=1)
                remaining = divmod(current_time - first_accessed_at, datetime.timedelta(seconds=60))
                minute = remaining[0]
                second = remaining[1].seconds
                raise LlmRateLimitException(f"{minute}分{second}秒") from e
            if e.code == 6:
                raise LlmConcurrentMessageException() from e
            raise e
        except Exception as e:
            if "one message" in str(e):
                raise LlmConcurrentMessageException() from e
            raise e

    def get_queue_info(self):
        return self.bot.queue

    @classmethod
    def register(cls):
        account_manager.register_type("chatgpt-web", Union[OpenAIAccessTokenAuth])
