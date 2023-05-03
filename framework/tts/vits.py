from typing import List

from framework.tts import TTSEngine
from framework.tts.tts import EmotionMarkupText, TTSVoice, TTSResponse


class VITSTTSEngine(TTSEngine):
    async def get_voice_list(self) -> List[TTSVoice]:
        pass

    async def speak(self, text: EmotionMarkupText, voice: TTSVoice) -> TTSResponse:
        pass

    async def get_supported_styles(self) -> List[str]:
        pass

