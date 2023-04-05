from loguru import logger


try:
    import edge_tts
    from pydub import AudioSegment


    async def edge_tts_speech(text: str, voice_name: str, path: str):
        try:
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(path + ".mp3")
            sound = AudioSegment.from_mp3(path + ".mp3")
            sound.export(path, format="wav")
            return True
        except Exception as err:
            logger.error(f"edge-tts api error: ", err)
            return False


except FileNotFoundError as e:
    async def edge_tts_speech(a=None, b=None, c=None):
        logger.error("错误：edge-tts 服务无法加载，请安装最新的 edge-tts、pydub 和 ffmpeg 运行库。")
        return None