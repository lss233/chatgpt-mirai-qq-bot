from edge_tts.exceptions import NoAudioReceived
from loguru import logger
import edge_tts

from constants import config
from utils.text_to_speech import TtsVoice, TtsVoiceManager

edge_tts_voices = {}


async def load_edge_tts_voices():
    if edge_tts_voices:
        return edge_tts_voices
    for el in await edge_tts.list_voices():
        if tts_voice := TtsVoice.parse(
            "edge", el.get('ShortName', ''), el.get('Gender', None)
        ):
            edge_tts_voices[tts_voice.alias] = tts_voice
    return edge_tts_voices


async def edge_tts_speech(text: str, tts_voice: TtsVoice, path: str):
    try:
        communicate = edge_tts.Communicate(text, tts_voice.full_name)
        output_path = path if path.endswith(".mp3") else f"{path}.mp3"
        await communicate.save(output_path)
        return output_path
    except NoAudioReceived:
        raise ValueError("语音生成失败，请检查音色设置是否正确。")
    except ValueError as e:
        if str(e).startswith("Invalid voice"):
            raise ValueError(
                f"不支持的音色：{tts_voice.full_name}"
                + "\n可用音色列表："
                + str([v.alias for v in await TtsVoiceManager.list_tts_voices(
                    "edge", config.text_to_speech.default_voice_prefix)])
            )
    except Exception as err:
        logger.exception(err)
        logger.error("[Edge TTS] API error: ", err)
        return None
