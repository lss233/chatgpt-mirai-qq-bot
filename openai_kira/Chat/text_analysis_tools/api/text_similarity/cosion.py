# -*- coding: utf-8 -*-


import jieba
from sklearn.metrics.pairwise import cosine_similarity
from ...api.keywords import STOPWORDS


class CosionSimilarity():
    """
    根据余弦函数计算相似性
    one-hot编码
    """

    def load_stopwords(self, stopwords_path):
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f]

    def cut_words(self, text, stopwords):
        return [word for word in jieba.cut(text) if word not in stopwords]

    def similarity(self, text1, text2):
        stopwords = self.load_stopwords(STOPWORDS)
        text1_words = set(self.cut_words(text1, stopwords))
        text2_words = set(self.cut_words(text2, stopwords))

        all_words = list(text1_words | text2_words)

        text1_vector = [1 if word in text1_words else 0 for word in all_words]
        text2_vector = [1 if word in text2_words else 0 for word in all_words]

        return cosine_similarity([text1_vector], [text2_vector])[0][0]


if __name__ == '__main__':
    text1 = "小明，你妈妈喊你回家吃饭啦"
    text2 = "回家吃饭啦，小明"
    similarity = CosionSimilarity()
    print(similarity.similarity(text1, text2))
