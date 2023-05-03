from typing import Generator

from loguru import logger


class Llm:
    """定义所有 Chatbot 的通用接口"""
    preset_name: str = "default"

    def get_queue_info(self): ...
    """获取内部队列"""

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.supported_models = []
        self.current_model = "default"
        ...

    async def ask(self, msg: str) -> Generator[str, None, None]: ...
    """向 AI 发送消息"""

    async def rollback(self): ...
    """回滚对话"""

    async def on_destoryed(self): ...
    """当会话被重置时，此函数被调用"""

    async def preset_ask(self, role: str, prompt: str):
        """以预设方式进行提问"""
        if role.endswith('bot') or role in {'assistant', 'chatgpt'}:
            logger.debug(f"[预设] 响应：{prompt}")
            yield prompt
        else:
            logger.debug(f"[预设] 发送：{prompt}")
            item = None
            async for item in self.ask(prompt): ...
            if item:
                logger.debug(f"[预设] Chatbot 回应：{item}")

    async def switch_model(self, model_name): ...
    """切换模型"""

    @classmethod
    def register(cls):
        pass


