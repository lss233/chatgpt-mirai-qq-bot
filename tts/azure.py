from typing import Dict, List

import httpx

import constants
from config import AzureConfig
from exceptions import TTSSpeakFailedException
from tts.tts import TTSEngine, TTSVoice, EmotionMarkupText, TTSResponse, VoiceFormat


class AzureTTSEngine(TTSEngine):
    client: httpx.AsyncClient

    def __init__(self, config: AzureConfig):
        self.client = httpx.AsyncClient(trust_env=True, proxies=constants.proxy)
        self.client.headers = {
            'Ocp-Apim-Subscription-Key': config.tts_speech_key
        }
        self.base_endpoint = f"https://{config.tts_speech_service_region}.tts.speech.microsoft.com/cognitiveservices"

    async def get_voice_list(self) -> List[TTSVoice]:
        response = await self.client.get(f"{self.base_endpoint}/voices/list")
        return [
            TTSVoice(
                engine="azure",
                codename=voice.get('ShortName'),
                full_name=voice.get('LocalName'),
                lang=[voice.get('Locale')],
                aliases=[voice.get('DisplayName')],
            )
            for voice in await response.json()
        ]

    async def speak(self, text: EmotionMarkupText, voice: TTSVoice) -> TTSResponse:
        # Convert text into SSML
        ssml_text = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{voice.lang[0]}'> <voice name='{voice.codename}'>"
        for style, text in text.texts:
            ssml_text += f"<mstts:express-as style='{style}'>{text}</mstts:express-as>"
        ssml_text += "</voice></speak>"

        headers = {
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm'
        }
        try:
            response = await self.client.post(f"{self.base_endpoint}/v1", headers=headers, content=ssml_text)
            response.raise_for_status()
        except Exception as e:
            raise TTSSpeakFailedException() from e
        return TTSResponse(VoiceFormat.Wav, response.content, str(text))

    async def get_supported_styles(self) -> List[str]:
        """
        支持的风格: https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/speech-synthesis-markup-voice#speaking-styles-and-roles
        """
        return ["advertisement_upbeat", "affectionate", "angry", "assistant", "calm", "chat", "cheerful", "customerservice", "depressed", "disgruntled", "documentary-narration", "embarrassed", "empathetic", "envious", "excited", "fearful", "friendly", "gentle", "hopeful", "lyrical", "narration-professional", "narration-relaxed", "newscast", "newscast-casual", "newscast-formal", "poetry-reading", "sad", "serious", "shouting", "sports_commentary", "sports_commentary_excited", "whispering", "terrified", "unfriendly"]


