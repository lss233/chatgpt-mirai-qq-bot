import os

from tempfile import NamedTemporaryFile
from typing import Optional

from graia.ariadne.message.element import Plain, Voice, Image
from loguru import logger

from constants import config
from utils.azure_tts import synthesize_speech, encode_to_silk
from utils.edge_tts import edge_tts_speech


async def get_tts_voice(elem, conversation_context) -> Optional[Voice]:
    if not isinstance(elem, Plain) or not str(elem):
        return None

    output_file = NamedTemporaryFile(mode='w+b', suffix='.wav', delete=False)
    output_file.close()

    logger.debug(f"[TextToSpeech] 开始转换语音 - {output_file.name} - {conversation_context.session_id}")
    if config.text_to_speech.engine == "vits":
        from utils.vits_tts import vits_api_instance
        if config.mirai or config.onebot:
            output_file.name = output_file.name.split(".")[0] + ".silk"
        if await vits_api_instance.process_message(str(elem), output_file.name):
            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return Voice(path=output_file.name)
    elif config.text_to_speech.engine == "azure":
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
    elif config.text_to_speech.engine == "edge":
        if await edge_tts_speech(str(elem), conversation_context.conversation_voice, output_file.name):
            output_file.name = f"{output_file.name}.mp3"
            voice = Voice(path=output_file.name)
            if config.mirai or config.onebot:
                voice = Voice(data_bytes=await encode_to_silk(await voice.get_bytes()))
            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return voice
    else:
        raise ValueError("不存在该文字转音频引擎，请检查配置文件是否正确")
