import os

from tempfile import NamedTemporaryFile
from typing import Optional

from graia.ariadne.message.element import Plain, Voice
from loguru import logger

from constants import config
from utils.azure_tts import synthesize_speech, encode_to_silk


async def get_tts_voice(elem, conversation_context) -> Optional[Voice]:
    if not isinstance(elem, Plain) or not str(elem):
        return None

    output_file = NamedTemporaryFile(mode='w+b', suffix='.wav', delete=False)
    output_file.close()

    logger.debug(f"[TextToSpeech] 开始转换语音 - {output_file.name} - {conversation_context.session_id}")
    if "vits" == config.text_to_speech.engine:
        from utils.vits_tts import VitsAPI
        if config.mirai or config.onebot:
            output_file.name = output_file.name + ".silk"
        if await VitsAPI.vits_api(str(elem), output_file.name):
            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return Voice(path=output_file.name)
    elif "azure" == config.text_to_speech.engine:
        if await synthesize_speech(
                str(elem),
                output_file.name,
                conversation_context.conversation_voice
        ):
            voice = Voice(path=output_file.name)
            if config.mirai or config.onebot:
                voice = Voice(data_bytes=await encode_to_silk(await voice.get_bytes()))

            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return voice

    else:
        raise ValueError("不存在该文字转音频引擎，请检查配置文件是否正确")
