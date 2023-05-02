import abc
from enum import Enum
from typing import List, Optional, Tuple, Dict
from loguru import logger

from exceptions import TTSNoVoiceFoundException, TTSEncodingFailedException


class VoiceFormat(Enum):
    """支持的所有音频格式"""
    Wav = "wav"
    Mp3 = "mp3"
    Silk = "silk"


class TTSResponse:
    """
    TTS引擎响应内容
    """
    data_bytes: Dict[VoiceFormat, bytes] = {}
    """语音的 格式:数据"""

    text: str
    """原文"""

    def __init__(self, format_: VoiceFormat, data_bytes: bytes, text: str):
        self.data_bytes[format_] = data_bytes
        self.text = text

    async def __to_silk(self) -> bytes:
        src_format = VoiceFormat.Wav if VoiceFormat.Wav in self.data_bytes else list(self.data_bytes.keys())[0]
        try:
            from graiax import silkcoder
            return await silkcoder.async_encode(
                self.data_bytes[src_format],
                audio_format=None,
                ios_adaptive=True,
                tencent=True
            )
        except ImportError as e:
            logger.warning("警告：Silk 转码模块无法加载，语音可能无法正常播放，请安装最新的 vc_redist 运行库。")
            raise TTSEncodingFailedException(src_format, VoiceFormat.Silk) from e

    def transcode(self, to_format: VoiceFormat) -> bytes:
        """音频转码"""
        if to_format in self.data_bytes:
            return self.data_bytes[to_format]
        if to_format == VoiceFormat.Silk:
            self.data_bytes[to_format] = await self.__to_silk()

        return self.data_bytes[to_format]


class EmotionMarkupText:
    """情绪标注数据格式"""

    texts: List[Tuple[str, str]] = []

    def __str__(self):
        """获取原始字符串"""
        return ''.join(block[1] for block in self.texts)

    def clear(self):
        """清空数据"""
        self.texts.clear()

    def append(self, text: str, emotion: str):
        """添加块"""
        self.texts.append((emotion, text))


class TTSVoice(metaclass=abc.ABCMeta):
    engine: str
    """引擎名称"""
    full_name: str
    """全程，用于展示"""
    lang: List[str] = []
    """支持语言"""
    codename: str
    """代码名称，用于 TTS Engine 调用"""
    aliases: List[str] = []
    """别名"""

    def __init__(self, engine: str, codename: str = None, full_name: str = None, lang: List[str] = None,
                 aliases: List[str] = None):
        self.engine = engine
        self.codename = codename
        self.full_name = full_name
        self.lang = lang
        self.aliases = aliases


class TTSEngine(metaclass=abc.ABCMeta):
    """语音引擎"""

    voices: List[TTSVoice] = []

    @abc.abstractmethod
    async def get_voice_list(self) -> List[TTSVoice]:
        """读取音色列表"""
        pass

    @abc.abstractmethod
    async def speak(self, text: EmotionMarkupText, voice: TTSVoice) -> TTSResponse:
        """说话"""
        pass

    @abc.abstractmethod
    async def get_supported_styles(self) -> List[str]:
        """
        获取支持的风格
        风格的名称本身应该表达出含义，这样我们交给 LLM 进行标注的时候就不需要另外再介绍，节约 token。
        """
        pass

    async def init(self):
        """初始化语音引擎"""
        self.voices = await self.get_voice_list()

    async def choose_voice(self, voice_name: str) -> Optional[TTSVoice]:
        """
        选择音色
        """
        if not self.voices:
            await self.get_voice_list()
        voice_name = voice_name.lower()
        try:
            return next(
                (
                    voice
                    for voice in self.voices
                    if voice_name in voice.aliases
                       or voice_name == voice.full_name
                       or voice_name == voice.codename
                )
            )
        except StopIteration as e:
            raise TTSNoVoiceFoundException(voice_name, self.voices) from e
