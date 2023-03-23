from typing import Generator
from adapter.botservice import BotAdapter
from constants import botManager
from exceptions import BotOperationNotSupportedException
from loguru import logger
import json
import requests
from urllib.parse import quote

class BardAdapter(BotAdapter):
    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self.account = botManager.pick('bard-cookie')
        self.headers = {
            "Cookie": self.account.cookie_content,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/2.0.4515.159 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': '',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        }
        self.get_at_token()
    
    def get_at_token(self):
        response = requests.get(
            "https://bard.google.com/",
            timeout=30,
            headers=self.headers,
        )
        self.at = quote(response.text.split('"SNlM0e":"')[1].split('","')[0])

    async def rollback(self):
        raise BotOperationNotSupportedException()

    async def on_reset(self):
        self.session_id = ""
        self.get_at_token()

    async def ask(self, prompt: str) -> Generator[str, None, None]:
        try:           
            url = "https://bard.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
            content = quote(prompt)
            raw_data = f"f.req=%5Bnull%2C%22%5B%5B%5C%22{content}%5C%22%5D%2Cnull%2C%5B%5C%22{self.session_id}%5C%22%2C%5C%22%5C%22%2C%5C%22%5C%22%5D%5D%22%5D&at={self.at}&"
            response = requests.post(
                url,
                timeout=30,
                headers=self.headers,
                data=raw_data,
            )
            if response.status_code != 200:
                print(f"Status code: {response.status_code}")
                print(response.text)
                raise Exception("Authentication failed")
            res = response.text.split("\n")
            for lines in res:
                if "wrb.fr" in lines:
                    data = json.loads(json.loads(lines)[0][2])
                    result = data[0][0]
                    self.session_id = data[1][0]                   
                    # result = re.sub(r'[^A-Za-z0-9 ,.]+', '', result) 
                    logger.info(f"bard: {result} -- {self.session_id}")
                    yield result
                    break

        except Exception as e:
            logger.exception(e)
            yield "出现了些错误"
            await self.on_reset()
            return

    async def preset_ask(self, role: str, text: str):
        yield None