# -*- coding: utf-8 -*-
# @Time    : 12/28/22 4:16 PM
# @FileName: Network.py
# @Software: PyCharm
# @Github    ：sudoskys

import asyncio
import atexit
from typing import Any

import httpx

__session_pool = {}


async def request(method: str,
                  url: str,
                  params: dict = None,
                  data: Any = None,
                  headers: dict = None,
                  proxy: str = "",
                  **kwargs
                  ):
    param = {
        "method": method.upper(),
        "url": url,
        "params": params,
        "data": data,
        "headers": headers,
    }
    param.update(kwargs)
    session = get_session(proxy=proxy)
    resp = await session.request(**param)
    content_length = resp.headers.get("content-length")
    if content_length and int(content_length) == 0:
        raise Exception("CONTENT LENGTH 0:Server Maybe Not Connected")
    return resp


def get_session(proxy: str = ""):
    global __session_pool
    loop = asyncio.get_event_loop()
    session = __session_pool.get(loop, None)
    if session is None:
        if proxy:
            proxies = {"all://": proxy}
            session = httpx.AsyncClient(timeout=300, proxies=proxies)
        else:
            session = httpx.AsyncClient(timeout=300)
        __session_pool[loop] = session
    return session


@atexit.register
def __clean():
    """
    程序退出清理操作。
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return

    async def __clean_task():
        await __session_pool[loop].close()

    if loop.is_closed():
        loop.run_until_complete(__clean_task())
    else:
        loop.create_task(__clean_task())
