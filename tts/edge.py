from typing import List

from edge_tts.exceptions import NoAudioReceived
import edge_tts
from io import BytesIO
import constants
from exceptions import TTSSpeakFailedException
from tts.tts import TTSEngine, TTSVoice, EmotionMarkupText, TTSResponse, VoiceFormat

edge_tts_voices = {}


class EdgeTTSEngine(TTSEngine):

    async def get_voice_list(self) -> List[TTSVoice]:
        voices = []
        for voice in await edge_tts.list_voices(proxy=constants.proxy):
            voices[voice.get('ShortName')] = TTSVoice(
                engine="edge",
                codename=voice.get('ShortName'),
                full_name=voice.get('DisplayName'),
                lang=[voice.get('Locale')],
                aliases=[voice.get('LocalName'), voice.get('DisplayName').lower()]
            )
        return voices

    async def speak(self, text: EmotionMarkupText, voice: TTSVoice) -> TTSResponse:
        try:
            communicate = edge_tts.Communicate(str(text), voice.codename)
            output = BytesIO()
            await communicate.save(output)
            output.seek(0)
            return TTSResponse(VoiceFormat.Mp3, output.read(), str(text))
        except NoAudioReceived as e:
            raise TTSSpeakFailedException() from e

    async def get_supported_styles(self) -> List[str]:
        """
        不支持任何风格
        """
        return []
