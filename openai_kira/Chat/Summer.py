# -*- coding: utf-8 -*-
# @Time    : 12/9/22 5:47 PM
# @FileName: Summer.py
# @Software: PyCharm
# @Github    ：sudoskys
"""
from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

# NO USE

pip install sumy

from snownlp import SnowNLP


class ChatUtils(object):

    @staticmethod
    def summary_v2(sentence, n):
        from sumy.nlp.stemmers import Stemmer
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.summarizers.lsa import LsaSummarizer as Summarizer
        from sumy.utils import get_stop_words
        # 差缺中文系统
        LANGUAGE = "english"
        # 统计中文字符数量
        if len([c for c in sentence if ord(c) > 127]) / len(sentence) > 0.5:
            _chinese = True
            LANGUAGE = "chinese"
        parser = PlaintextParser.from_string(sentence, Tokenizer(LANGUAGE))
        stemmer = Stemmer(LANGUAGE)
        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(LANGUAGE)
        _words = summarizer(parser.document, n)
        _words = [str(i) for i in _words]
        _return = "".join(_words)
        return _return

    @staticmethod
    def summary(sentence, n):
        # 差缺中文系统
        _chinese = False
        # 统计中文字符数量
        if len([c for c in sentence if ord(c) > 127]) / len(sentence) > 0.5:
            _chinese = True
        if _chinese:
            try:
                s = SnowNLP(sentence)  # str为之前去掉符号的中文字符串
                _sum = (s.summary(round(n)))  # 进行总结 summary
                # _sum = jiagu.summarize(sentence, round(n / 10))
            except Exception as e:
                _sum = [sentence]
            content = ",".join(_sum)  # 摘要
        else:
            import nltk
            nltk.download('punkt')
            nltk.download('stopwords')
            tokens = nltk.word_tokenize(sentence)
            # 分句
            sentences = nltk.sent_tokenize(sentence)
            # 计算词频
            frequencies = nltk.FreqDist(tokens)
            # 计算每个句子的得分
            scores = {}
            for sentence_ in sentences:
                score = 0
                for word in nltk.word_tokenize(sentence_):
                    if word in frequencies:
                        score += frequencies[word]
                scores[sentence_] = score
            # 按照得分顺序排序句子
            sorted_sentences = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            # 返回前 num_sentences 个句子
            return_num = round(n / 2)
            if len(sorted_sentences) < return_num:
                return_num = len(sorted_sentences)
            _list = [sentence_[0] for sentence_ in sorted_sentences[:return_num]]
            content = ",".join(_list)
        if len(content.strip(" ")) == 0:
            content = sentence
        return content
"""
