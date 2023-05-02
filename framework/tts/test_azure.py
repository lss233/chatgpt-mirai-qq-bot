from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from config import AzureConfig
from framework.tts.azure import AzureTTSEngine, TTSVoice, EmotionMarkupText, TTSResponse, VoiceFormat

fakeConfig = AzureConfig(
    tts_speech_key="fake_key",
    tts_speech_service_region="fake_region"
)


class TestAzureTTSEngine(IsolatedAsyncioTestCase):
    async def test_get_voice_list(self):
        expected_voices = [TTSVoice(
            engine="azure",
            codename="zh-CN-YunxiNeural",
            full_name="云希",
            lang=["zh-CN"],
            aliases=["Yunxi"]
        ),
            TTSVoice(
                engine="azure",
                codename="ga-IE-OrlaNeural",
                full_name="Orla",
                lang=["ga-IE"],
                aliases=["Orla"]
            )
        ]
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value.json.return_value = [
                {
                    "Name": "Microsoft Server Speech Text to Speech Voice (zh-CN, YunxiNeural)",
                    "DisplayName": "Yunxi",
                    "LocalName": "云希",
                    "ShortName": "zh-CN-YunxiNeural",
                    "Gender": "Male",
                    "Locale": "zh-CN",
                    "LocaleName": "Chinese (Mandarin, Simplified)",
                    "StyleList": [
                        "narration-relaxed",
                        "embarrassed",
                        "fearful",
                        "cheerful",
                        "disgruntled",
                        "serious",
                        "angry",
                        "sad",
                        "depressed",
                        "chat",
                        "assistant",
                        "newscast"
                    ],
                    "SampleRateHertz": "24000",
                    "VoiceType": "Neural",
                    "Status": "GA",
                    "RolePlayList": [
                        "Narrator",
                        "YoungAdultMale",
                        "Boy"
                    ],
                    "WordsPerMinute": "293"
                },
                {
                    "Name": "Microsoft Server Speech Text to Speech Voice (ga-IE, OrlaNeural)",
                    "DisplayName": "Orla",
                    "LocalName": "Orla",
                    "ShortName": "ga-IE-OrlaNeural",
                    "Gender": "Female",
                    "Locale": "ga-IE",
                    "LocaleName": "Irish (Ireland)",
                    "SampleRateHertz": "24000",
                    "VoiceType": "Neural",
                    "Status": "GA",
                    "WordsPerMinute": "139"
                },
            ]
            engine = AzureTTSEngine(fakeConfig)
            voices = await engine.get_voice_list()
            self.assertListEqual(voices, expected_voices)

    async def test_speak(self):
        expected_response = TTSResponse(
            VoiceFormat.Wav,
            b"fake audio data",
            "hello world"
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.content = b"fake audio data"
            engine = AzureTTSEngine(fakeConfig)
            response = await engine.speak(
                EmotionMarkupText([("neutral", "hello world")]),
                TTSVoice(
                    engine="edge",
                    codename="fake",
                    full_name="fake",
                    lang=["en-US"],
                    aliases=["fake"]
                )
            )
            self.assertEqual(response.text, expected_response.text)

    async def test_get_supported_styles(self):
        expected_styles = [
            "advertisement_upbeat", "affectionate", "angry", "assistant", "calm", "chat", "cheerful", "customerservice",
            "depressed", "disgruntled", "documentary-narration", "embarrassed", "empathetic", "envious", "excited",
            "fearful", "friendly", "gentle", "hopeful", "lyrical", "narration-professional", "narration-relaxed",
            "newscast", "newscast-casual", "newscast-formal", "poetry-reading", "sad", "serious", "shouting",
            "sports_commentary", "sports_commentary_excited", "whispering", "terrified", "unfriendly"
        ]
        engine = AzureTTSEngine(fakeConfig)
        styles = await engine.get_supported_styles()
        self.assertEqual(styles, expected_styles)

    async def test_speak_failure(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception()
            engine = AzureTTSEngine(fakeConfig)
            with self.assertRaises(Exception):
                await engine.speak(
                    EmotionMarkupText([("neutral", "hello world")]),
                    TTSVoice(
                        engine="azure",
                        codename="fake",
                        full_name="fake",
                        lang=["en-US"],
                        aliases=["fake"]
                    )
                )
