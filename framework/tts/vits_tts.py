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
        elif self.id is None:
            self.id = await self.voice_speakers_check()

        self.initialized = True

    def check_id_exists(self, json_list, given_id):
        for item in json_list:
            for key, value in item.items():
                if str(given_id) in [key, value]:
                    return key, value
        return None, None

    async def set_id(self, new_id):
        json_array = await self.get_json_array()
        id_found, voice_name = self.check_id_exists(json_array, new_id)

        if not voice_name:
            raise Exception("不存在该语音音色，请检查配置文件")

        self.id = id_found
        return voice_name

    async def get_json_array(self):
        url = f"{config.vits.api_url}/speakers"

        try:
            async with ClientSession(timeout=ClientTimeout(total=config.vits.timeout)) as session:
                async with session.post(url=url) as res:
                    json_array = await res.json()
                    return json_array["VITS"]

        except Exception as e:
            logger.error(f"获取语音音色列表失败: {str(e)}")
            raise Exception("获取语音音色列表失败，请检查网络连接和API设置")

    async def voice_speakers_check(self, new_id=None):
        json_array = await self.get_json_array()

        try:
            if new_id is not None:
                integer_number = int(new_id)
            elif config.text_to_speech.default is not None:
                integer_number = int(config.text_to_speech.default)
            else:
                raise ValueError("默认语音音色未设置，请检查配置文件")
            voice_name = self.check_id_exists(json_array, integer_number)
        except ValueError:
            logger.error("vits引擎中音色只能为纯数字")
            return None

        if not voice_name:
            raise Exception("不存在该语音音色，请检查配置文件")

        return integer_number

    async def get_voice_data(self, text, lang, voice_type):
        url = f"{config.vits.api_url}?text={text}&lang={lang}&id={self.id}&format={voice_type}&length={config.vits.speed}"

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
        lang = self.lang

        if lang == "auto": return text

        patterns = {
            "mix": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u4e00-\u9fff]+|[\u3040-\u309f\u30a0-\u30ff]+|\w+|[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+',
            "zh": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u4e00-\u9fff\p{P}]+',
            "ja": r'[\!\"\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\>\=\?\@\[\]\{\}\\\\\^\_\`\~\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\u3040-\u309f\u30a0-\u30ff\p{P}]+',
        }

        regex = patterns.get(lang, '')
        matches = re.findall(regex, text)
        return (
            ''.join(
                f'[ZH]{match}[ZH]'
                if re.search(patterns['zh'], match)
                else f'[JA]{match}[JA]'
                if re.search(patterns['ja'], match)
                else match
                if re.search(
                    '[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+', match
                )
                else "[ZH]还有一些我不会说，抱歉[ZH]"
                for match in matches
            )
            if lang == "mix"
            else ''.join(matches)
        )

    async def response(self, text, voice_type, path):
        text = self.linguistic_process(text)
        content = await self.get_voice_data(text, self.lang, voice_type)
        if content is not None:
            return self.save_voice_file(content, path)

    async def process_message(self, message, path, voice_type):
        if not self.initialized:
            await self.initialize()

        return await self.response(message, voice_type, path)


vits_api_instance = VitsAPI()
