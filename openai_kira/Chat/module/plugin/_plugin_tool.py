# -*- coding: utf-8 -*-
# @Time    : 12/27/22 8:00 PM
# @FileName: plugins.py
# @Software: PyCharm
# @Github    ：sudoskys

from loguru import logger
from transformers import GPT2TokenizerFast

import openai_kira
from openai_kira.utils import Network
from openai_kira.utils.Talk import Talk

gpt_tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

netTool = Network


class PromptTool(object):
    @staticmethod
    def isStrIn(prompt: str, keywords: list):
        isIn = False
        for i in keywords:
            if i in prompt:
                isIn = True
        return isIn

    @staticmethod
    def isStrAllIn(prompt: str, keywords: list):
        isIn = True
        for i in keywords:
            if i not in prompt:
                isIn = False
        return isIn

    @staticmethod
    def match_enhance(prompt):
        import re
        match = re.findall(r"\[(.*?)\]", prompt)
        match2 = re.findall(r"\"(.*?)\"", prompt)
        match3 = re.findall(r"\((.*?)\)", prompt)
        match.extend(match2)
        match.extend(match3)
        return match


class NlP(object):
    @staticmethod
    def get_webServerStopSentence():
        return openai_kira.webServerStopSentence

    @staticmethod
    def get_is_filter_url():
        return openai_kira.webServerUrlFilter

    @staticmethod
    def summary(text: str, ratio: float = 0.5) -> str:
        return Talk.tfidf_summarization(sentence=text, ratio=ratio)

    @staticmethod
    def nlp_filter_list(prompt, material: list):
        if not material or not isinstance(material, list):
            return []
        logger.trace(f"NLP")
        # 双匹配去重
        while len(material) > 2:
            prev_len = len(material)
            _pre = material[0]
            _afe = material[1]
            sim = Talk.simhash_similarity(pre=_pre, aft=_afe)
            if sim < 12:
                _remo = _afe if len(_afe) > len(_pre) else _pre
                # 移除过于相似的
                material.remove(_remo)
            if len(material) == prev_len:
                break

        while len(material) > 2:
            prev_len = len(material)
            material_len = len(material)
            for i in range(0, len(material), 2):
                if i + 1 >= material_len:
                    continue
                _pre = material[i]
                _afe = material[i + 1]
                sim = Talk.cosion_sismilarity(pre=_pre, aft=_afe)
                if sim > 0.7:
                    _remo = _afe if len(_afe) > len(_pre) else _pre
                    # 移除过于相似的
                    material.remove(_remo)
                    material_len = material_len - 1
            if len(material) == prev_len:
                break

        # 去重排序+删除无关
        material_ = {item: -1 for item in material}
        material = list(material_.keys())
        _top_table = {}
        for item in material:
            _top_table[item] = Talk.cosion_sismilarity(pre=prompt, aft=item)
        material = {k: v for k, v in _top_table.items() if v > 0.15}
        # 搜索引擎比相似度算法靠谱所以注释掉了
        # material = OrderedDict(sorted(material.items(), key=lambda t: t[1]))
        # logger.trace(material)

        # 关联度指数计算
        _key = Talk.tfidf_keywords(prompt, topK=7)
        _score = 0
        _del_keys = []
        for k, i in material.items():
            for ir in _key:
                if ir in k:
                    _score += 1
            if _score / len(_key) < 0.3:
                _del_keys.append(k)
        for k in _del_keys:
            material.pop(k)
        return list(material.keys())
