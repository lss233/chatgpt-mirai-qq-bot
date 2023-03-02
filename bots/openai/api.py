from typing import Generator

from aiohttp import ClientSession

class OpenAIChatBot:
    config: dict()

    session: ClientSession

    is_no_quota: bool = False

    def __int__(self, api_key: str):
        self.session = ClientSession()
        self.api_key = api_key

    async def ask(self, messages: list, user: str = None) -> Generator[str]:
        async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.engine,
                    "messages": messages,
                    "stream": True,
                    # kwargs
                    "temperature": self.config.get("temperature", 0.7),
                    "top_p": self.config.get("top_p", 1),
                    "n": self.config.get("n", 1),
                    "user": user,
                },
                stream=True,
        ) as r:
            async for line in r.content:
                yield line

    @classmethod
    def pick(cls):
        pass
