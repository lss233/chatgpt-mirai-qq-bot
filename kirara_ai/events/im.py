from kirara_ai.im.adapter import IMAdapter


class IMEvent:
    def __init__(self, im: IMAdapter):
        self.im = im
        
    def __repr__(self):
        return f"{self.__class__.__name__}(im={self.im})"

class IMAdapterStarted(IMEvent):
    pass

class IMAdapterStopped(IMEvent):
    pass
