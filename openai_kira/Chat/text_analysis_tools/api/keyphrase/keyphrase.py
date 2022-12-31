# -*- coding: utf-8 -*-


import re

import jieba
import jieba.analyse
import numpy as np


# from wordcloud import WordCloud


class KeyPhraseExtraction():
    def __init__(self, topk=50, method='tfidf', with_word=True):
        """
        :param topk: 根据前多少关键词生成短语
        :param method: tfidf / textrank
        :param with_word: 最后输出结果是否包含关键词
        """
        self.topk = topk
        self.method = method
        self.with_word = with_word

    def cut_sentences(self, text):
        """文本分句，然后分词"""
        sentences = re.findall(".*?[。？！]", text)
        cut_sentences = [jieba.lcut(sent) for sent in sentences]
        return cut_sentences

    def key_words_extraction(self, text):
        """提取关键词"""
        keywords_score = []
        if self.method == 'tfidf':
            keywords_score = jieba.analyse.extract_tags(text, topK=self.topk, withWeight=True)
        elif self.method == 'textrank':
            keywords_score = jieba.analyse.textrank(text, topK=self.topk, withWeight=True)
        return {word: score for word, score in keywords_score}

    def key_phrase_extraction(self, text):
        keyword_score = self.key_words_extraction(text)
        keywords = keyword_score.keys()
        cut_sentences = self.cut_sentences(text)
        # print(keywords)
        # 将相邻的关键词进行拼接
        key_phrase = []
        for sent in cut_sentences:
            temp = []
            for word in sent:
                if word in keywords:
                    temp.append(word)
                else:
                    if len(temp) > 1:
                        if temp not in key_phrase:
                            key_phrase.append(temp)
                    temp = []

        # 短语之间可能存在冗余信息，进行过滤
        key_phrase_filter = []
        for phrase in key_phrase:
            flag = False
            for item in key_phrase_filter:
                if len(set(phrase) & set(item)) >= min(len(set(phrase)), len(set(item))) / 2.0:
                    flag = True
                    break
            if not flag:
                key_phrase_filter.append(phrase)

        # 给短语赋值权重, 设置短语最多包含三个关键词
        keyphrase_weight = {''.join(phrase[-3:]): np.mean([keyword_score[word] for word in phrase[-3:]])
                            for phrase in key_phrase_filter}

        if self.with_word:
            key_phrase_str = '|'.join(keyphrase_weight)
            for word, weight in keyword_score.items():
                if word not in key_phrase_str:
                    keyphrase_weight[word] = weight
        keyphrase_weight = dict(sorted(keyphrase_weight.items(), key=lambda x: x[1], reverse=True)[:self.topk])

        return keyphrase_weight

    """
    def wordcloud(self, keyphrrase_weight, save_path='./wordcloud.png', with_mask=False, mask_pic=MASK_PATH):
        font = FONT_PATH
        mask = mask_pic
        mask = np.array(Image.open(mask))
        if with_mask:
            wc = WordCloud(
                background_color='white',
                width=800,
                height=800,
                mask=mask,
                font_path=font,
                # stopwords=stopword
            )
        else:
            wc = WordCloud(
                background_color='white',
                width=800,
                height=800,
                # mask=mask,
                font_path=font,
                # stopwords=stopword
            )
        wc.generate_from_frequencies(keyphrrase_weight)  # 绘制图片
        wc.to_file(save_path)  # 保存图片
    """


if __name__ == '__main__':
    with open('./data/test', encoding='utf-8') as f:
        text = f.read()
    key_phrase_extractor = KeyPhraseExtraction(topk=20)
    key_phrase = key_phrase_extractor.key_phrase_extraction(text)
    key_phrase_extractor.wordcloud(key_phrase)
