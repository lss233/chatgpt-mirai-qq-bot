# -*- coding: utf-8 -*-
# @Time    : 12/27/22 7:19 PM
# @FileName: module.py
# @Software: PyCharm
# @Github    ：sudoskys

from pydantic import BaseModel
from loguru import logger


class PluginParam(BaseModel):
    text: str = ""
    server: dict = []


class PluginConfig(BaseModel):
    text: str = ""
    server: list = {}


class ChatPlugin(object):
    PLUGINS = {}

    async def process(self, param: PluginParam, plugins=None) -> list:
        if plugins is None:
            plugins = []
        _return = []
        if not plugins:
            plugins = self.PLUGINS.keys()
        for plugin_name in plugins:
            try:
                if not self.PLUGINS.get(plugin_name):
                    raise LookupError(f"{plugin_name} not installed!")
                obj = self.PLUGINS[plugin_name]()
                if await obj.check(param):
                    config = param.dict()
                    config.update({"server": param.server.get(plugin_name) if param.server.get(plugin_name) else []})
                    plugin_config: PluginConfig
                    plugin_config = PluginConfig(**config)
                    # print(plugin_config.dict())
                    text = await obj.process(plugin_config)
                    _return.extend(text)
                    # Log
                    logger.debug(f"{plugin_name}:{text}")
            except Exception as e:
                logger.error(f"Plugin:{plugin_name} --Error:{e}")
        return _return

    @classmethod
    def plugin_register(cls, plugin_name):
        def wrapper(plugin):
            logger.success(f"LoadPlugin:{plugin_name}")
            cls.PLUGINS.update({plugin_name: plugin})
            return plugin

        return wrapper
