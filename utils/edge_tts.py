from loguru import logger
import edge_tts


async def edge_tts_speech(text: str, voice_name: str, path: str):
    try:
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(f"{path}.mp3")
        return True
    except ValueError as e:
        if str(e).startswith("Invalid voice"):
            raise ValueError(
                f"不支持的音色：{voice_name}"
                + "\n音色列表："
                + str(await edge_tts.list_voices())
            )
    except Exception as err:
        logger.exception(err)
        logger.error("[Edge TTS] API error: ", err)
        return False
