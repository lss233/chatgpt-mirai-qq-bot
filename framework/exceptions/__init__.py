class PresetNotFoundException(ValueError): ...


class LlmConcurrentMessageException(Exception): ...


class BotTypeNotFoundException(Exception): ...


class NoAvailableBotException(Exception): ...


class LlmOperationNotSupportedException(Exception): ...


class CommandRefusedException(Exception): ...


class LlmRateLimitException(Exception):
    estimated_at: str

    def __init__(self, estimated_at):
        self.estimated_at = estimated_at


class APIKeyNoFundsError(Exception): ...


class DrawingFailedException(Exception):
    def __init__(self):
        self.__cause__ = None


class TTSSpeakFailedException(Exception): ...


class TTSNoVoiceFoundException(Exception): ...


class TTSEncodingFailedException(Exception): ...


class LlmRequestTimeoutException(Exception): ...


class LlmRequestFailedException(Exception): ...


class LLmAuthenticationFailedException(Exception): ...
