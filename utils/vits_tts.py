import regex as re
from loguru import logger
from constants import config
from aiohttp import ClientSession, ClientTimeout

__all__ = ['VitsAPI']


class VitsAPI:
    def __init__(self):
        self.lang = config.vits.lang
        self.id = None
        self.initialized = False

    async def initialize(self, new_id=None):
        if new_id is not None:
            await self.set_id(new_id)
        else:
            self.id = await self.voice_speakers_check()

        self.initialized = True

    def check_id_exists(self, json_dict, given_id):
        return json_dict[given_id].get(str(given_id), False)

    async def set_id(self, new_id):
        json_array = await self.get_json_array()
        voice_name = self.check_id_exists(json_array, new_id)

        if not voice_name:
            raise Exception("不存在该语音音色，请检查配置文件")

        self.id = new_id
        return voice_name

    async def get_json_array(self):
        url = f"{config.vits.api_url}/speakers"

        async with ClientSession(timeout=ClientTimeout(total=config.vits.timeout)) as session:
            async with session.post(url=url) as res:
                return await res.json()

    async def voice_speakers_check(self, new_id=None):
        json_array = await self.get_json_array()
        vits_list = json_array["VITS"]

        try:
            if new_id is not None:
                integer_number = int(new_id)
            elif config.text_to_speech.default is not None:
                integer_number = int(config.text_to_speech.default)
            else:
                raise ValueError("默认语音音色未设置，请检查配置文件")
            voice_name = self.check_id_exists(vits_list, integer_number)
        except ValueError:
            logger.error("vits引擎中音色只能为纯数字")
            return None

        if not voice_name:
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
            "mix": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u4e00-\u9fff]+|[\u3040-\u309f\u30a0-\u30ff]+|\w+|[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+',
            "zh": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u4e00-\u9fff\p{P}]+',
            "ja": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u3040-\u309f\u30a0-\u30ff\p{P}]+',
        }
        regex = patterns.get(lang, '')
        matches = re.findall(regex, text)
        if lang == "mix":
            matched_text = ''.join(
                '[ZH]' + match + '[ZH]' if re.search(patterns['zh'], match) else
                '[JA]' + match + '[JA]' if re.search(patterns['ja'], match) else
                match if re.search('[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+', match) else
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
        if not self.initialized:
            await self.initialize()

        if config.mirai or config.onebot:
            output_file = await self.response(message, "silk", path)
        else:
            output_file = await self.response(message, "wav", path)

        return output_file


vits_api_instance = VitsAPI()


async def vits_api(message: str, path: str):
    await vits_api_instance.initialize()
    return await vits_api_instance.process_message(message, path)
