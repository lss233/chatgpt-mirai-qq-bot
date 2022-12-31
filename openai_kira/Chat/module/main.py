# -*- coding: utf-8 -*-
# @Time    : 12/27/22 9:48 PM
# @FileName: main.py
# @Software: PyCharm
# @Github    ：sudoskys
from .platform import ChatPlugin, PluginParam


async def get_reply(prompt: str, table: dict) -> str:
    processor = ChatPlugin()
    processed = await processor.process(param=PluginParam(text=prompt, server=table))  # , plugins=['search'])
    reply = "\n".join(processed) if processed else ""
    return reply


async def test_plugin(prompt: str, table: dict, plugins: list) -> str:
    processor = ChatPlugin()
    processed = await processor.process(param=PluginParam(text=prompt, server=table), plugins=plugins)
    reply = "\n".join(processed) if processed else ""
    return reply
