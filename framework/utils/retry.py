import asyncio
from loguru import logger


def retry(exceptions, tries=4, delay=3, backoff=2):
    """
    异步方法的指数重试装饰器函数
    :param exceptions: 异常类型，可以是单个类型或者元组类型
    :param tries: 最大重试次数，默认为4次
    :param delay: 初始重试延迟时间，默认为3秒
    :param backoff: 重试延迟时间增长倍数，默认为2
    :return: 装饰器函数
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            _tries = tries
            _delay = delay
            while _tries > 0:
                try:
                    async for result in func(*args, **kwargs):
                        yield result
                    return
                except exceptions as e:
                    logger.exception(e)
                    logger.error(f"处理请求时遇到错误, 将在 {_delay} 秒后重试...")
                    await asyncio.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            async for result in func(*args, **kwargs):
                yield result

        return wrapper

    return decorator
