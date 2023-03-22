import asyncio
from typing import Generator

from adapter.botservice import BotAdapter
from constants import botManager, config
from exceptions import BotOperationNotSupportedException
from loguru import logger
import json
import requests
from urllib.parse import quote

class BardAdapter(BotAdapter):
    cookieData = None
    count: int = 0

    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        account = botManager.pick('bard-cookie')
        self.cookieData = []
        for line in account.cookie_content.split("; "):
            name, value = line.split("=", 1)
            self.cookieData.append({"name": name, "value": value})


    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.count = 0
        # await self.bot.reset()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        self.count = self.count + 1
        try:
            HEADERS = {
                "Cookie": config.bard.accounts[0].cookie_content,
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/2.0.4515.159 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': '',
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            }           
            url = "https://bard.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
            content = quote(prompt)
            raw_data = f"f.req=%5Bnull%2C%22%5B%5B%5C%22{content}%5C%22%5D%2Cnull%2C%5B%5C%22%5C%22%2C%5C%22%5C%22%2C%5C%22%5C%22%5D%5D%22%5D&at=AGLd_IRhS9xAFjj55MV2uEqs5MkX%3A1679450282221&"
            response = requests.post(
                url,
                timeout=30,
                headers=HEADERS,
                data=raw_data,
           )
            if response.status_code != 200:
                print(f"Status code: {response.status_code}")
                print(response.text)
                raise Exception("Authentication failed")
            res = response.text.split("\n")
            for lines in res:
                if "wrb.fr" in lines:
                    data = json.loads(lines)
                    result = json.loads(data[0][2])[0][0]
                    logger.info(f"bard: {result}")
            yield True, str(result)      
        except Exception as e:
            logger.exception(e)
            yield "出现了些错误"
            # await self.on_reset()
            return

    async def preset_ask(self, role: str, text: str):
        yield None
