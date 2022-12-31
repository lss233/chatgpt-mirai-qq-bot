# -*- coding: utf-8 -*-
# @Time    : 12/27/22 8:20 PM
# @FileName: week.py
# @Software: PyCharm
# @Github    ：sudoskys

from ..platform import ChatPlugin, PluginConfig
from ._plugin_tool import PromptTool
from loguru import logger
import os

modulename = os.path.basename(__file__).strip(".py")


@ChatPlugin.plugin_register(modulename)
class Week(object):
    def __init__(self):
        self._server = None
        self._text = None
        self._week_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        self._week_key = ["星期", "星期几", "时间", "周几", "周一", "周二", "周三", "周四", "周五", "周六"]

    def requirements(self):
        return []

    async def check(self, params: PluginConfig) -> bool:
        if PromptTool.isStrIn(prompt=params.text, keywords=self._week_list + self._week_key):
            return True
        return False

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
        onw = bj_dt.weekday()
        _return.append(f"Now {self._week_list[onw]}")
        logger.trace(_return)
        return _return
