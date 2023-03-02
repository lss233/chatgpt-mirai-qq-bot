from aiohttp import ClientSession


class OpenAIChatWebBot:
    config: dict()

    session: ClientSession


    def __int__(self):
        self.session = ClientSession()

    async def ask(self, role: str, messages: list):
        pass

    @classmethod
    def pick(cls):
        pass
