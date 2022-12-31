# -*- coding: utf-8 -*-
# @Time    : 12/16/22 2:34 PM
# @FileName: Talk.py
# @Software: PyCharm
# @Github    ：sudoskys
import re
import time
from ..Chat.text_analysis_tools.api.keywords.tfidf import TfidfKeywords
from ..Chat.text_analysis_tools.api.summarization.textrank_summarization import TextRankSummarization
from ..Chat.text_analysis_tools.api.summarization.tfidf_summarization import TfidfSummarization
from ..Chat.text_analysis_tools.api.text_similarity.simhash import SimHashSimilarity
from ..Chat.text_analysis_tools.api.text_similarity.cosion import CosionSimilarity
from transformers import GPT2TokenizerFast

gpt_tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


class Talk(object):
    @staticmethod
    def textrank_summarization(sentence: str, ratio=0.2):
        """
        采用 textrank 进行摘要抽取
        :param sentence: 待处理语句
        :param ratio: 摘要占文本长度的比例
        :return:
        """
        _sum = TextRankSummarization(ratio=ratio)
        _sum = _sum.analysis(sentence)
        return _sum

    @staticmethod
    def tfidf_summarization(sentence: str, ratio=0.5):
        """
        采用tfidf进行摘要抽取
        :param sentence:
        :param ratio: 摘要占文本长度的比例
        :return:
        """
        _sum = TfidfSummarization(ratio=ratio)
        _sum = _sum.analysis(sentence)
        return _sum

    @staticmethod
    def cosion_sismilarity(pre, aft):
        """
        基于余弦计算文本相似性 0 - 1 (1为最相似)
        :return: 余弦值
        """
        _cos = CosionSimilarity()
        _sim = _cos.similarity(pre, aft)
        return _sim

    @staticmethod
    def simhash_similarity(pre, aft):
        """
        采用simhash计算文本之间的相似性
        :return:
        """
        simhash = SimHashSimilarity()
        sim = simhash.run_simhash(pre, aft)
        # print("simhash result: {}\n".format(sim))
        return sim

    @staticmethod
    def tfidf_keywords(keywords, delete_stopwords=True, topK=5, withWeight=False):
        """
        tfidf 提取关键词
        :param keywords:
        :param delete_stopwords: 是否删除停用词
        :param topK: 输出关键词个数
        :param withWeight: 是否输出权重
        :return: [(word, weight), (word1, weight1)]
        """
        tfidf = TfidfKeywords(delete_stopwords=delete_stopwords, topK=topK, withWeight=withWeight)
        return tfidf.keywords(keywords)

    @staticmethod
    def tokenizer(s: str) -> float:
        """
        谨慎的计算器，会预留 5 token
        :param s:
        :return:
        """
        # 统计中文字符数量
        return len(gpt_tokenizer.encode(s))

    @staticmethod
    def english_sentence_cut(text) -> list:
        list_ = list()
        for s_str in text.split('.'):
            if '?' in s_str:
                list_.extend(s_str.split('?'))
            elif '!' in s_str:
                list_.extend(s_str.split('!'))
            else:
                list_.append(s_str)
        return list_

    @staticmethod
    def chinese_sentence_cut(text) -> list:
        text = re.sub('([。！？\?])([^’”])', r'\1\n\2', text)
        # 普通断句符号且后面没有引号
        text = re.sub('(\.{6})([^’”])', r'\1\n\2', text)
        # 英文省略号且后面没有引号
        text = re.sub('(\…{2})([^’”])', r'\1\n\2', text)
        # 中文省略号且后面没有引号
        text = re.sub('([.。！？\?\.{6}\…{2}][’”])([^’”])', r'\1\n\2', text)
        # 断句号+引号且后面没有引号
        return text.split("\n")

    def cut_chinese_sentence(self, text):
        p = re.compile("“.*?”")
        listr = []
        index = 0
        for i in p.finditer(text):
            temp = ''
            start = i.start()
            end = i.end()
            for j in range(index, start):
                temp += text[j]
            if temp != '':
                temp_list = self.chinese_sentence_cut(temp)
                listr += temp_list
            temp = ''
            for k in range(start, end):
                temp += text[k]
            if temp != ' ':
                listr.append(temp)
            index = end
        return listr

    @staticmethod
    def isCode(sentence):
        code = False
        _reco = [
            '("',
            '")',
            ").",
            "()",
            "!=",
            "=="
        ]
        _t = len(_reco)
        _r = 0
        for i in _reco:
            if i in sentence:
                _r += 1
        if _r > _t / 2:
            code = True
        rms = [
            "print_r(",
            "var_dump(",
            'NSLog( @',
            'println(',
            '.log(',
            'print(',
            'printf(',
            'WriteLine(',
            '.Println(',
            '.Write(',
            'alert(',
            'echo(',
        ]
        for i in rms:
            if i in sentence:
                code = True
        return code

    @staticmethod
    def get_language(sentence: str):
        language = "english"
        # 差缺中文系统
        if len([c for c in sentence if ord(c) > 127]) / len(sentence) > 0.5:
            language = "chinese"
        if Talk.isCode(sentence):
            language = "code"
        return language

    def cut_sentence(self, sentence: str) -> list:
        language = self.get_language(sentence)
        if language == "chinese":
            _reply_list = self.cut_chinese_sentence(sentence)
        elif language == "english":
            # from nltk.tokenize import sent_tokenize
            _reply_list = self.english_sentence_cut(sentence)
        else:
            _reply_list = [sentence]
        if len(_reply_list) < 1:
            return [sentence]
        return _reply_list

    def cut_ai_prompt(self, prompt: str) -> list:
        """
        切薄负载机
        :param prompt:
        :return:
        """
        _some = prompt.split(":", 1)
        _head = ""
        if len(_some) > 1:
            _head = f"{_some[0]}:"
            prompt = _some[1]
        _reply = self.cut_sentence(prompt)
        _prompt_list = []
        for item in _reply:
            _prompt_list.append(f"{_head}{item.strip()}")
        _prompt_list = list(filter(None, _prompt_list))
        return _prompt_list
