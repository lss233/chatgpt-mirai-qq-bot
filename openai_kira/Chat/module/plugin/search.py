# -*- coding: utf-8 -*-
# @Time    : 12/16/22 1:37 PM
# @FileName: __init__.py.py
# @Software: PyCharm
# @Github    ：sudoskys
# import gzip
import os
import random
from urllib.parse import urlparse
from loguru import logger

from ..platform import ChatPlugin, PluginConfig
from bs4 import BeautifulSoup
from ._plugin_tool import NlP, PromptTool, gpt_tokenizer, netTool

info_cache = {}

modulename = os.path.basename(__file__).strip(".py")


@ChatPlugin.plugin_register(modulename)
class Search(object):
    def __init__(self):
        self._server = None
        self._text = None

    def requirements(self):
        return ["httpx", "beautifulsoup4"]

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

    async def get_resource(self,
                           query: str = "KKSK 是什么意思？"
                           ) -> list:
        def get_tld(url):
            """
            获取顶级域名
            :param url:
            :return:
            """
            parsed_url = urlparse(url)
            return parsed_url.netloc

        if self._server:
            _url = self._server.format(query)
        else:
            return []
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, defalte",
            "Connection": "keep-alive",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Host": f"{get_tld(self._server)}",
            "Referer": f"https://www.{get_tld(self._server)}/",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0"
        }
        html = await netTool.request("GET", url=_url, headers=headers, timeout=10)
        htmltext = html.text
        # 匹配
        sret = {}
        if "html" in htmltext:
            rs = BeautifulSoup(htmltext, "html.parser")
            # print(rs.text)
            if "goog" in self._server:
                target = ["html", rs.select("div > span")]
            else:
                target = ["html", rs.select("div")]
        else:
            target = ["text", htmltext.split("\n")]
        # 分类
        if target[0] == "html":
            for i in target[1]:
                if i.parent.select("a[href]"):
                    continue
                res = i.parent.text
                cr = self.filter_sentence(query=query, sentence=res)
                if cr:
                    sret[cr] = 0
        else:
            for i in target[1]:
                cr = self.filter_sentence(query=query, sentence=i)
                if cr:
                    sret[cr] = 0
        return list(sret.keys())

    async def check(self, params: PluginConfig) -> bool:
        prompt = params.text
        if len(prompt) < 80:
            if (prompt.startswith("介绍") or prompt.startswith("查询") or prompt.startswith("你知道")
                or "2022年" in prompt or "2023年" in prompt) \
                    or (len(prompt) < 20 and "?" in prompt or "？" in prompt):
                return True
        return False

    async def process(self, params: PluginConfig) -> list:
        global info_cache

        # Prompt
        prompt = params.text
        match = PromptTool.match_enhance(prompt)
        if match:
            prompt = match[0]
        else:
            if prompt.startswith("介绍") or prompt.startswith("查询") or prompt.startswith("你知道"):
                prompt.replace("介绍", "").replace("查询", "").replace("你知道", "").replace("吗？", "")
        self._text = prompt
        # Server
        self._server = params.server
        if isinstance(params.server, list):
            self._server = random.choice(params.server)
        if info_cache.get(params.text):
            return info_cache.get(params.text)

        # 校验
        if not all([self._server, self._text]):
            return []
        # GET
        _returner = []
        _list = await self.get_resource(self._text)
        _list = _list[:10]
        _returner = NlP.nlp_filter_list(prompt=self._text, material=_list)
        logger.trace(_returner)
        info_cache[self._text] = _returner
        _pre = 0
        info = []
        for i in _returner:
            if _pre > 220:
                break
            info.append(i)
            _pre += len(gpt_tokenizer.encode(i))
        return info
