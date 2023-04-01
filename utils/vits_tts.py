import os
import re
import datetime
from loguru import logger
from constants import config
from aiohttp import ClientSession, ClientTimeout


__all__ = ['VitsAPI']


class VitsAPI:
    def __init__(self):
        self.lang = config.vits.lang
        self.id = None

    async def initialize(self):
        self.id = await self.voice_speakers_check()

    def check_id_exists(self, json_array, given_id):
        return any(str(given_id) in item for item in json_array)

    async def voice_speakers_check(self):
        url = f"{config.vits.api_url}/speakers"

        async with ClientSession(timeout=ClientTimeout(total=config.vits.timeout)) as session:
            async with session.post(url=url) as res:
                json_array = await res.json()

                try:
                    integer_number = int(config.text_to_speech.default)
                    result = self.check_id_exists(json_array, integer_number)
                except ValueError:
                    logger.error("vits引擎中音色只能为纯数字")
                    return None

                if not result:
                    raise Exception("不存在该语音音色，请检查配置文件")

                return integer_number

    async def get_voice_data(self, text, lang, format):
        url = f"{config.vits.api_url}?text=[LENGTH={config.vits.speed}]{text}&lang={lang}&id={self.id}&format={format}"

        async with ClientSession(timeout=ClientTimeout(total=config.vits.timeout)) as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"请求失败：{response.status}")
                        return None
                    return await response.read()
            except TimeoutError as e:
                logger.error(f"请求语音超时：{text}")
                return None
            except Exception as e:
                logger.error(f"请求失败：{str(e)}")
                return None

    def save_voice_file(self, content, save_path):

        try:
            with open(save_path, 'wb') as f:
                f.write(content)
            logger.success(f"[VITS TTS] 文件已保存到：{save_path}")
        except IOError as e:
            logger.error(f"[VITS TTS] 文件写入失败：{str(e)}")
            return None

        return save_path

    def linguistic_process(self, text):
        if len(text) > 150:
            text = "这句话太长了，抱歉"

        lang = self.lang
        patterns = {
            "mix": r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+',
            "zh": r'[\u4e00-\u9fff]+',
            "ja": r'[\u3040-\u309f\u30a0-\u30ff]+',
        }
        regex = patterns.get(lang, '')
        matches = re.findall(regex, text)
        if lang == "mix":
            matched_text = ''.join(
                '[ZH]' + match + '[ZH]' if re.search('[\u4e00-\u9fff]+', match) else
                '[JA]' + match + '[JA]' if re.search('[\u3040-\u309f\u30a0-\u30ff]+', match) else
                "[ZH]还有一些我不会说，抱歉[ZH]"
                for match in matches
            )
        else:
            matched_text = ''.join(matches)

        return matched_text

    async def response(self, text, format, path):
        text = self.linguistic_process(text)
        content = await self.get_voice_data(text, self.lang, format)
        if content is not None:
            return self.save_voice_file(content, path)

    async def process_message(self, message, path):
        if config.mirai or config.onebot:
            output_file = await self.response(message, "silk", path)
        else:
            output_file = await self.response(message, "wav", path)

        return output_file

    @staticmethod
    async def vits_api(message: str, path: str):
        vits_api_instance = VitsAPI()
        await vits_api_instance.initialize()
        return await vits_api_instance.process_message(message, path)
