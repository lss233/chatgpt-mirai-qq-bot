import os
from enum import Enum

from tempfile import NamedTemporaryFile
from typing import Optional

from graia.ariadne.message.element import Plain, Voice, Image
from loguru import logger

from constants import config
from utils.azure_tts import synthesize_speech, encode_to_silk

tts_voice_dic = {}
"""各引擎的音色列表"""


class VoiceType(Enum):
    Wav = "wav"
    Mp3 = "mp3"
    Silk = "silk"


class TtsVoice:

    def __init__(self):
        self.engine = None
        """参考：edge, azure, vits"""
        self.gender = None
        """参考：Male, Female"""
        self.full_name = None
        """参考：zh-CN-liaoning-XiaobeiNeural, af-ZA-AdriNeural, am-ET-MekdesNeural"""
        self.lang = None
        """参考：zh, af, am"""
        self.region = None
        """参考：CN, ZA, ET"""
        self.name = None
        """参考：XiaobeiNeural, AdriNeural, MekdesNeural"""
        self.alias = None
        """参考：xiaobei, adri, mekdes"""
        self.sub_region = None
        """参考：liaoning"""

    def description(self):
        return f"{self.alias}: {self.full_name}{f' - {self.gender}' if self.gender else ''}"

    @staticmethod
    def parse(engine, voice: str, gender=None):
        tts_voice = TtsVoice()
        tts_voice.engine = engine
        tts_voice.full_name = voice
        tts_voice.gender = gender
        if engine in ["edge", "azure"]:
            """如：zh-CN-liaoning-XiaobeiNeural、uz-UZ-SardorNeural"""
            voice_info = voice.split("-")
            if len(voice_info) < 3:
                return None
            lang = voice_info[0]
            region = voice_info[1]
            if len(voice_info) == 4:
                sub_region = voice_info[2]
                name = voice_info[3]
            else:
                sub_region = None
                name = voice_info[2]
            alias = name.replace("Neural", "").lower()
            tts_voice.lang = lang
            tts_voice.region = region
            tts_voice.name = name
            tts_voice.alias = alias
            tts_voice.sub_region = sub_region
        else:
            tts_voice.lang = voice
            tts_voice.alias = voice

        return tts_voice


class TtsVoiceManager:
    """tts音色管理"""

    @staticmethod
    def parse_tts_voice(tts_engine, voice_name) -> TtsVoice:
        if tts_engine != "edge":
            # todo support other engines
            return TtsVoice.parse(tts_engine, voice_name)
        from utils.edge_tts import edge_tts_voices
        if "edge" not in tts_voice_dic:
            tts_voice_dic["edge"] = edge_tts_voices
        _voice_dic = tts_voice_dic["edge"]
        if _voice := TtsVoice.parse(tts_engine, voice_name):
            return _voice_dic.get(_voice.alias, None)
        if voice_name in _voice_dic:
            return _voice_dic[voice_name]

    @staticmethod
    async def list_tts_voices(tts_engine, voice_prefix):
        """获取可用哪些音色"""

        def match_voice_prefix(full_name):
            if isinstance(voice_prefix, str):
                return full_name.startswith(voice_prefix)
            if isinstance(voice_prefix, list):
                for _prefix in voice_prefix:
                    if full_name.startswith(_prefix):
                        return True
                return False

        if tts_engine == "edge":
            from utils.edge_tts import load_edge_tts_voices
            if "edge" not in tts_voice_dic:
                tts_voice_dic["edge"] = await load_edge_tts_voices()
            _voice_dic = tts_voice_dic["edge"]
            return [v for v in _voice_dic.values() if voice_prefix is None or match_voice_prefix(v.full_name)]
        # todo support other engines
        return []


async def get_tts_voice(elem, conversation_context, voice_type=VoiceType.Wav) -> Optional[Voice]:
    if not isinstance(elem, Plain) or not str(elem):
        return None

    voice_suffix = f".{voice_type.value}"

    output_file = NamedTemporaryFile(mode='w+b', suffix=voice_suffix, delete=False)
    output_file.close()

    logger.debug(f"[TextToSpeech] 开始转换语音 - {conversation_context.session_id}")
    if config.text_to_speech.engine == "vits":
        from utils.vits_tts import vits_api_instance
        if await vits_api_instance.process_message(str(elem), output_file.name, voice_type.value):
            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return Voice(path=output_file.name)
    elif config.text_to_speech.engine == "azure":
        tts_output_file_name = (f"{output_file.name}.{VoiceType.Wav.value}"
                                if voice_type == VoiceType.Silk else output_file.name)
        if await synthesize_speech(
                str(elem),
                tts_output_file_name,
                conversation_context.conversation_voice
        ):
            voice = Voice(path=tts_output_file_name)
            if voice_type == VoiceType.Silk:
                voice = Voice(data_bytes=await encode_to_silk(await voice.get_bytes()))

            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return voice
    elif config.text_to_speech.engine == "edge":
        from utils.edge_tts import edge_tts_speech
        tts_output_file_name = await edge_tts_speech(
            str(elem), conversation_context.conversation_voice, output_file.name)
        if tts_output_file_name:
            output_file.name = tts_output_file_name
            voice = Voice(path=output_file.name)
            if voice_type == VoiceType.Silk:
                voice = Voice(data_bytes=await encode_to_silk(await voice.get_bytes()))
            logger.debug(f"[TextToSpeech] 语音转换完成 - {output_file.name} - {conversation_context.session_id}")
            return voice
    else:
        raise ValueError("不存在该文字转音频引擎，请检查配置文件是否正确")
