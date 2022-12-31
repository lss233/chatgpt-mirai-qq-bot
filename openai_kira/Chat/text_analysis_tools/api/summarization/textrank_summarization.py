# -*- coding: utf-8 -*-


import jieba
import numpy as np
from nltk.cluster.util import cosine_distance
from ..summarization import STOPWORDS as STOPWORDS_PATH

MIN_SEQ_LEN = 0


def load_stopwords(file_path):
    with open(file_path, encoding='utf-8') as f:
        return [line.strip() for line in f]


def split_doc(doc, stopwords=None):
    if not stopwords:
        stopwords = []

    sentences = []
    cut_sentences = []
    origin_sentences = []

    while len(doc) > 0:
        for i in range(len(doc)):
            if doc[i] in ['。', '！', '?', '？']:
                sentences.append(doc[:i + 1])
                doc = doc[i + 1:]
                break
    for sent in sentences:
        if len(sent) > MIN_SEQ_LEN:
            cut_sentences.append([word for word in jieba.cut(sent) if word not in stopwords])
            origin_sentences.append(sent)
    return origin_sentences, cut_sentences


def sentence_similarity(sent1, sent2):
    """
    计算两个句子之间的相似性
    :param sent1:
    :param sent2:
    :return:
    """
    all_words = list(set(sent1 + sent2))

    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)

    for word in sent1:
        vector1[all_words.index(word)] += 1

    for word in sent2:
        vector2[all_words.index(word)] += 1

    # cosine_distance 越大越不相似
    return 1 - cosine_distance(vector1, vector2)


def build_similarity_matrix(sentences):
    """
    构建相似矩阵
    :param sentences:
    :return:
    """
    S = np.zeros((len(sentences), len(sentences)))
    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2:
                continue
            S[idx1][idx2] = sentence_similarity(sentences[idx1], sentences[idx2])
    # 将矩阵正则化
    for idx in range(len(S)):
        if S[idx].sum == 0:
            continue
        S[idx] /= S[idx].sum()

    return S


def pagerank(A, eps=0.0001, d=0.85):
    P = np.ones(len(A)) / len(A)
    while True:
        new_P = np.ones(len(A)) * (1 - d) / len(A) + d * A.T.dot(P)
        delta = abs(new_P - P).sum()
        if delta <= eps:
            return new_P
        P = new_P


class TextRankSummarization:
    def __init__(self, ratio):
        self.ratio = ratio
        self.stopwords = load_stopwords(STOPWORDS_PATH)

    def analysis(self, doc):
        origin_sentences, cut_sentences = split_doc(doc, stopwords=self.stopwords)

        S = build_similarity_matrix(cut_sentences)

        sentences_ranks = pagerank(S)

        sentences_ranks = [item[0] for item in sorted(enumerate(sentences_ranks), key=lambda item: -item[1])]

        selected_sentences_index = sorted(sentences_ranks[:int(len(origin_sentences) * self.ratio)])

        summary = []
        for idx in selected_sentences_index:
            summary.append(origin_sentences[idx])

        return ''.join(summary)
