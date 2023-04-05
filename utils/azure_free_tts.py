import asyncio

import threading
from loguru import logger

# from constants import config

try:
    from graiax import silkcoder


    async def mp3_to_silk(input_data: bytes) -> bytes:
        return await silkcoder.async_encode(
            input_data,
            audio_format='mp3',
            ios_adaptive=True
        )
except ImportError as e:
    async def encode_to_silk(a=None):
        logger.warning("警告：Silk 转码模块无法加载，语音可能无法正常播放，请安装最新的 vc_redist 运行库。")
        return a

    # if config.text_to_speech.engine == 'azure':
    #     asyncio.run(encode_to_silk())

try:
    # import azure.cognitiveservices.speech as speechsdk
    import edge_tts


    async def azure_free_speech(text: str, voice_name: str, path: str):
        try:
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(path)
            return True
        except Exception as err:
            logger.error(f"Azure free api error: ", err)
            return False



except FileNotFoundError as e:
    async def synthesize_speech(a=None, b=None, c=None):
        logger.error("错误：Azure TTS 服务无法加载，请安装最新的 vc_redist 运行库。")
        logger.error("参考链接：")
        logger.error("https://github.com/lss233/chatgpt-mirai-qq-bot/issues/447")
        return None

    # if config.text_to_speech.engine == 'azure':
    #     asyncio.run(synthesize_speech())
