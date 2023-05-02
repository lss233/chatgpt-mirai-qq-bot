from unittest import IsolatedAsyncioTestCase

from framework.tts import EdgeTTSEngine
from framework.tts.tts import TTSVoice, TTSResponse, VoiceFormat, EmotionMarkupText


class TestEdgeTTSEngine(IsolatedAsyncioTestCase):
    async def test_get_voice_list(self):
        # Test if get_voice_list returns a list of TTSVoice objects
        engine = EdgeTTSEngine()
        voice_list = await engine.get_voice_list()
        self.assertIsInstance(voice_list, list)
        for voice in voice_list:
            self.assertIsInstance(voice, TTSVoice)

    async def test_speak(self):
        # Test if speak returns a TTSResponse object with non-empty audio data
        engine = EdgeTTSEngine()
        voice = TTSVoice(engine="edge", codename="af-ZA-AdriNeural", full_name="Microsoft Server Speech Text to Speech Voice (af-ZA, AdriNeural)", lang=["af-ZA"], aliases=["Adri"])
        text = EmotionMarkupText([("claim", "Hello, world!")])
        response = await engine.speak(text, voice)
        self.assertIsInstance(response, TTSResponse)
        self.assertIsNotNone(response.data_bytes[VoiceFormat.Mp3])

    async def test_get_supported_styles(self):
        # Test if get_supported_styles returns an empty list
        engine = EdgeTTSEngine()
        supported_styles = await engine.get_supported_styles()
        self.assertIsInstance(supported_styles, list)
        self.assertEqual(len(supported_styles), 0)
