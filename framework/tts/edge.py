from typing import List

import edge_tts
from io import BytesIO
import constants
from framework.exceptions import TTSSpeakFailedException
from framework.tts.tts import TTSEngine, TTSVoice, EmotionMarkupText, TTSResponse, VoiceFormat

edge_tts_voices = {}


class EdgeTTSEngine(TTSEngine):

    async def get_voice_list(self) -> List[TTSVoice]:
        return [
            TTSVoice(
                engine="edge",
                codename=voice.get('ShortName'),
                full_name=voice.get('FriendlyName'),
                lang=[voice.get('Locale')],
                aliases=[
                    voice.get(
                        'Name',
                        f'Microsoft Server Speech Text to Speech Voice ({voice.get("Locale")}, {voice.get("FriendlyName")}Neural)',
                    )
                    .split(',')[1]
                    .split('Neural')[0]
                ],
            )
            for voice in await edge_tts.list_voices(proxy=constants.proxy)
        ]

    async def speak(self, text: EmotionMarkupText, voice: TTSVoice) -> TTSResponse:
        communicate = edge_tts.Communicate(str(text), voice.codename)
        output = BytesIO()
        written_audio = False
        with BytesIO() as audio:
            async for message in communicate.stream():
                if message["type"] == "audio":
                    audio.write(message["data"])
                    written_audio = True
        if not written_audio:
            raise TTSSpeakFailedException(
                "No audio was received from the service, so the file is empty."
            )
        output.seek(0)
        return TTSResponse(VoiceFormat.Mp3, output.read(), str(text))

    def get_supported_styles(self) -> List[str]:
        """
        不支持任何风格
        """
        return []
