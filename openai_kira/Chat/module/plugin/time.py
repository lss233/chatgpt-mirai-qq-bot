# -*- coding: utf-8 -*-
# @Time    : 12/27/22 8:43 PM
# @FileName: time.py
# @Software: PyCharm
# @Github    ：sudoskys

from ..platform import ChatPlugin, PluginConfig
from ._plugin_tool import PromptTool
import os
from loguru import logger

modulename = os.path.basename(__file__).strip(".py")


@ChatPlugin.plugin_register(modulename)
class Week(object):
    def __init__(self):
        self._server = None
        self._text = None
        self._time = ["time", "多少天", "几天", "时间", "几点", "今天", "昨天", "明天", "几月", "几月", "几号",
                      "几个月",
                      "天前"]

    async def check(self, params: PluginConfig) -> bool:
        if PromptTool.isStrIn(prompt=params.text, keywords=self._time):
            return True
        return False

    def requirements(self):
        return []

    async def process(self, params: PluginConfig) -> list:
        _return = []
        self._text = params.text
        # 校验
        if not all([self._text]):
            return []
        # GET
        from datetime import datetime, timedelta, timezone
        utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
        now = bj_dt.strftime("%Y-%m-%d %H:%M")
        _return.append(f"Current Time UTC8 {now}")
        logger.trace(_return)
        return _return
