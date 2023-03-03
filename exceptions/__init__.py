class PresetNotFoundException(ValueError): ...

class ConcurrentMessageException(Exception): ...
class BotRatelimitException(Exception):
    estimated_at: str
    def __init__(self, estimated_at):
        self.estimated_at = estimated_at