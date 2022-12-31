# -*- coding: utf-8 -*-
# @Time    : 12/28/22 10:29 PM
# @FileName: _zhihu.py
# @Software: PyCharm
# @Github    ：sudoskys

from ..platform import ChatPlugin, PluginConfig
from ._plugin_tool import PromptTool, NlP
from loguru import logger
import os

modulename = os.path.basename(__file__).strip(".py")


@ChatPlugin.plugin_register(modulename)
class Zhihu(object):
    def __init__(self):
        self._server = None
        self._text = None
        self._zhihu = ["知乎", "大V", "评价"]

    def requirements(self):
        return ["playwright", "beautifulsoup4"]

    async def check(self, params: PluginConfig) -> bool:
        if PromptTool.isStrIn(prompt=params.text, keywords=self._zhihu):
            return True
        return False

    @staticmethod
    def filter_sentence(query, sentence) -> str:
        import re
        stop_sentence = NlP.get_webServerStopSentence()
        if not isinstance(stop_sentence, list):
            stop_sentence = ["下面就让我们",
                             "小编", "一起来看一下", "小伙伴们",
                             "究竟是什么意思", "看影片", "看人次", "？", "是什么", "什么意思", "意思介绍", " › ",
                             "游侠", "为您提供", "今日推荐", "線上看", "线上看",
                             "高清观看", "点击下载", "带来不一样的", "..去看看",
                             "最新章节", "电影网", "资源下载：", "高清全集在线",
                             "在线观看地址"]  # "?","_哔哩哔哩_bilibili","知乎",
        skip = False
        for ir in stop_sentence:
            if ir in sentence:
                skip = True
        if NlP.get_is_filter_url():
            pas = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            _link = re.findall(pas, sentence)
            if _link:
                for i in _link:
                    sentence = sentence.replace(i, "")
            _link = re.findall("(?:[\w-]+\.)+[\w-]+", sentence)
            if _link:
                if len("".join(_link)) / len(sentence) > 0.7:
                    skip = True
                for i in _link:
                    sentence = sentence.replace(i, "")
        if skip:
            return ""
        # 处理数据
        sentence = sentence.strip(".").strip("…").replace('\xa0', '').replace('   ', '').replace("/r", '')
        sentence = sentence.replace("/v", '').replace("/s", '').replace("/p", '').replace("/a", '').replace("/d", '')
        sentence = sentence.replace("，", ",").replace("。", ".").replace("\n", ".")
        if 18 < len(sentence):
            return sentence.strip(".")
        else:
            return ""

    async def get_content(self, query, html):
        from bs4 import BeautifulSoup
        rs = BeautifulSoup(html, "html.parser")
        target = rs.select("div")
        logger.trace(target)
        sret = {}
        for i in target:
            cr = self.filter_sentence(query=query, sentence=i)
            if cr:
                sret[cr] = 0
        return list(sret.keys())

    async def process(self, params: PluginConfig) -> list:
        _return = []
        self._text = params.text
        # 校验
        if not all([self._text]):
            return []
        # 校验
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            logger.error("You Need Install:`pip install duckduckgo_search`")
            return []
        # GET
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            js = """
            Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
            """
            page = await browser.new_page()
            await page.add_init_script(js)
            await page.goto(f"https://www.zhihu.com/search?type=content&q={self._text}", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            html = await page.content()
            await browser.close()
        result = await self.get_content(query=self._text, html=html)
        _return.extend(result)
        logger.trace(_return)
        return _return
