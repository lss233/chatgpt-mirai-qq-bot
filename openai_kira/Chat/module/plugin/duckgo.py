# -*- coding: utf-8 -*-
# @Time    : 12/28/22 1:44 PM
# @FileName: duckgo.py
# @Software: PyCharm
# @Github    ：sudoskys

import os

from loguru import logger
from ..platform import ChatPlugin, PluginConfig
from ._plugin_tool import PromptTool, NlP, gpt_tokenizer, netTool

modulename = os.path.basename(__file__).strip(".py")


class Duckgo(object):
    cache = set()
    PAGINATION_STEP = 25

    async def get_page(self, payload, page):
        from duckduckgo_search.utils import _normalize
        page_results = []
        page_data = []
        payload["s"] = max(self.PAGINATION_STEP * (page - 1), 0)
        try:
            resp = await netTool.request("POST", "https://links.duckduckgo.com/d.js", params=payload)
            resp.raise_for_status()
            page_data = resp.json().get("results", None)
        except Exception as e:
            logger.error("Duckgo Client Error")
        if not page_data:
            return page_results
        for row in page_data:
            if "n" not in row and row["u"] not in self.cache:
                self.cache.add(row["u"])
                body = _normalize(row["a"])
                if body:
                    page_results.append(
                        {
                            "title": _normalize(row["t"]),
                            "href": row["u"],
                            "body": body,
                        }
                    )
        return page_results

    async def get_result(self,
                         keywords,
                         region="wt-wt",
                         safesearch="moderate",
                         max_results=None,
                         time=None,
                         page=1
                         ):
        from duckduckgo_search.utils import _get_vqd
        if not keywords:
            return None
        vqd = _get_vqd(keywords)
        if not vqd:
            return None

        # prepare payload
        safe_search_base = {"On": 1, "Moderate": -1, "Off": -2}
        payload = {
            "q": keywords,
            "l": region,
            "p": safe_search_base[safesearch.capitalize()],
            "s": 0,
            "df": time,
            "o": "json",
            "vqd": vqd,
        }
        results = await self.get_page(page=page, payload=payload)
        results = results[:max_results]
        return results


@ChatPlugin.plugin_register(modulename)
class DuckGo(object):
    def __init__(self):
        self._server = None
        self._text = None

    @staticmethod
    def filter_sentence(query, sentence) -> str:
        import re
        stop_sentence = NlP.get_webServerStopSentence()
        if not isinstance(stop_sentence, list):
            stop_sentence = ["下面就让我们",
                             "小编", "一起来看一下", "小伙伴们",
                             "究竟是什么意思", "看影片", "看人次", "？", "是什么", "什么意思", "意思介绍", " › ",
                             "游侠", "为您提供", "今日推荐", "線上看", "线上看",
                             "高清观看", "?", "知乎", "点击下载"]  #
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
            return sentence
        else:
            return ""

    def requirements(self):
        return ["duckduckgo_search"]

    async def check(self, params: PluginConfig) -> bool:
        prompt = params.text
        if len(prompt) < 80:
            if (prompt.startswith("介绍") or prompt.startswith("查询") or prompt.startswith("你知道")
                or "2022年" in prompt or "2023年" in prompt) \
                    or (len(prompt) < 20 and "?" in prompt or "？" in prompt):
                return True
        return False

    async def process(self, params: PluginConfig) -> list:
        _return = []
        prompt = params.text
        match = PromptTool.match_enhance(prompt)
        if match:
            prompt = match[0]
        else:
            if prompt.startswith("介绍") or prompt.startswith("查询") or prompt.startswith("你知道"):
                prompt.replace("介绍", "").replace("查询", "").replace("你知道", "").replace("吗？", "")
        self._text = prompt
        # 校验
        if not all([self._text]):
            return []
        # 校验
        try:
            from duckduckgo_search import ddg
        except Exception as e:
            logger.error("You Need Install:`pip install duckduckgo_search`")
            return []
        # GET
        _results = await Duckgo().get_result(keywords=self._text)
        if not _results:
            return []
        _list = [self.filter_sentence(query=self._text, sentence=i["body"]) for i in _results]
        _list = [x for x in _list if x]
        _list = _list[:7]
        logger.trace(f"初步筛选：{_list}")
        _returner = NlP.nlp_filter_list(prompt=self._text, material=_list)
        logger.trace(f"NLP筛选：{_returner}")
        _pre = 0
        info = []
        _sum = NlP.summary(text="。||".join(_returner), ratio=0.8)
        _returner = _sum.split("||")
        for i in _returner:
            if _pre > 300:
                break
            info.append(i)
            _pre += len(gpt_tokenizer.encode(i))
        return info
