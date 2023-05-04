from typing import List, Union
from xml.dom.minidom import getDOMImplementation, Document, Element

import httpx

import constants
from config import AzureConfig
from framework.exceptions import TTSSpeakFailedException
from framework.tts.tts import TTSEngine, TTSVoice, EmotionMarkupText, TTSResponse, VoiceFormat

impl = getDOMImplementation()

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
        if response.status_code == 401:
            raise RuntimeError("Invalid Azure TTS api_key. Azure TTS 配置有误，请重新填写！")
        response.raise_for_status()
        return [
            TTSVoice(
                engine="azure",
                codename=voice.get('ShortName'),
                full_name=voice.get('LocalName'),
                lang=[voice.get('Locale')],
                aliases=[voice.get('DisplayName')],
            )
            for voice in response.json()
        ]

    async def speak(self, text: Union[str, EmotionMarkupText], voice: TTSVoice) -> TTSResponse:
        ssml_doc: Document = impl.createDocument("http://www.w3.org/2001/10/synthesis", "speak", None)
        speak_element: Element = ssml_doc.documentElement
        speak_element.setAttribute("xmlns", "http://www.w3.org/2001/10/synthesis")
        speak_element.setAttribute("xmlns:mstts", "https://www.w3.org/2001/mstts")
        speak_element.setAttribute("version", "1.0")
        speak_element.setAttribute("xml:lang", voice.lang[0])
        voice_document: Element = ssml_doc.createElement("voice")
        voice_document.setAttribute("name", voice.codename)

        if isinstance(text, str):
            voice_text = ssml_doc.createTextNode(text)
            voice_document.appendChild(voice_text)
        else:
            for style, text in text.texts:
                express_as_document = ssml_doc.createElement("mstts:express-as")
                express_as_document.setAttribute("style", style)
                express_as_text = ssml_doc.createTextNode(text)
                express_as_document.appendChild(express_as_text)
                voice_document.appendChild(express_as_document)

        speak_element.appendChild(voice_document)

        headers = {
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm'
        }
        try:
            response = await self.client.post(f"{self.base_endpoint}/v1", headers=headers, content=ssml_doc.toxml())
            response.raise_for_status()

            return TTSResponse(VoiceFormat.Wav, await response.aread(), str(text))
        except Exception as e:
            raise TTSSpeakFailedException() from e

    def get_supported_styles(self) -> List[str]:
        """
        支持的风格: https://learn.microsoft.com/zh-cn/azure/cognitive-services/speech-service/speech-synthesis-markup-voice#speaking-styles-and-roles
        """
        return ["advertisement_upbeat", "affectionate", "angry", "assistant", "calm", "chat", "cheerful", "customerservice", "depressed", "disgruntled", "documentary-narration", "embarrassed", "empathetic", "envious", "excited", "fearful", "friendly", "gentle", "hopeful", "lyrical", "narration-professional", "narration-relaxed", "newscast", "newscast-casual", "newscast-formal", "poetry-reading", "sad", "serious", "shouting", "sports_commentary", "sports_commentary_excited", "whispering", "terrified", "unfriendly"]


