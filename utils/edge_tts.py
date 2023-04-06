from loguru import logger
import edge_tts


async def edge_tts_speech(text: str, voice_name: str, path: str):
    try:
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(path + ".mp3")
        return True
    except Exception as err:
        logger.error(f"[Edge TTS] API error: ", err)
        return False
