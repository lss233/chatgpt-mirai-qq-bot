import atexit
import sys
from loguru import logger

class ExitHooks(object):
    def __init__(self):
        self.exit_code = None
        self.exception = None

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc

hooks = ExitHooks()
hooks.hook()

def foo():
    if hooks.exit_code is not None or hooks.exception is not None:
        if type(hooks.exception) is KeyboardInterrupt:
            return
        logger.error("看样子程序似乎没有正常退出。")
        logger.exception(hooks.exception)
        logger.error("你可以在这里阅读常见问题的解决方案：")
        logger.error("https://github.com/lss233/chatgpt-mirai-qq-bot/issues/85")
atexit.register(foo)