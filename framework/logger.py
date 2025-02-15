import re
from typing import Any
from loguru import logger
import os
from datetime import datetime

# 创建 logs 文件夹
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 配置日志格式和颜色
logger.remove()  # 移除默认的日志处理器

# 定义日志格式
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[tag]: <12}</cyan> | "
    "<level>{message}</level>"
)

# 添加控制台日志处理器
logger.add(
    sink=lambda msg: print(msg.strip()),  # 输出到控制台
    format=log_format,
    level="DEBUG",
    colorize=True,
)

# 添加文件日志处理器，支持日志轮转
log_file = os.path.join(LOG_DIR, "log_{time:YYYY-MM-DD}.log")
logger.add(
    sink=log_file,
    format=log_format,
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="7 days",  # 保留7天的日志
    compression="zip",  # 压缩旧日志文件
    colorize=False,
)

# 全局日志实例
_global_logger = logger

def get_logger(tag: str):
    """
    获取带有特定标签的日志记录器
    :param tag: 日志标签
    :return: 日志记录器
    """
    return _global_logger.bind(tag=tag)

class HypercornLoggerWrapper:
    def __init__(self, logger):
        self.logger = logger
        
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.critical(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.error(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        log_fmt = re.sub(r'%\((\w+)\)s', r'{\1}', message)
        atoms = args[0] if args else {}
        self.logger.info(log_fmt, **atoms)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.debug(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.exception(message, *args, **kwargs)

    def log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.log(level, message, *args, **kwargs)

def get_async_logger(tag: str):
    """
    获取带有特定标签的日志记录器
    :param tag: 日志标签
    :return: 日志记录器
    """
    return HypercornLoggerWrapper(_global_logger.bind(tag=tag))
