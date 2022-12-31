# -*- coding: utf-8 -*-

import os
import jieba
import jieba.analyse
from ..keywords import STOPWORDS


class TfidfKeywords:
    def __init__(self, delete_stopwords=True, topK=20, withWeight=False):
        if delete_stopwords:
            jieba.analyse.set_stop_words(STOPWORDS)

        self.topk = topK
        self.with_wight = withWeight

    def keywords(self, sentence):
        return jieba.analyse.extract_tags(sentence, topK=self.topk, withWeight=self.with_wight)
