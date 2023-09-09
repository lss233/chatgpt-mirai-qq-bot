import atexit
import os
import signal
import sys

from loguru import logger

from constants import config


class ExitHooks(object):
    def __init__(self):
        self._orig_exit = None
        self.exit_code = None
        self.exception = None

    def replace_exit(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc


def foo(hooks):
    if hooks.exit_code is not None or hooks.exception is not None:
        if isinstance(hooks.exception, (KeyboardInterrupt, type(None))):
            return
        logger.error("看样子程序似乎没有正常退出。")
        logger.exception(hooks.exception)
        logger.error("你可以在这里阅读常见问题的解决方案：")
        logger.error(
            "https://github.com/lss233/chatgpt-mirai-qq-bot/issues/85")
        raise hooks.exception


def exit_gracefully(signal, frame):
    logger.warning("程序即将退出...".format(signal))
    os._exit(0)


def hook():
    hooks = ExitHooks()
    hooks.replace_exit()
    atexit.register(foo, hooks)

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGABRT, exit_gracefully)
