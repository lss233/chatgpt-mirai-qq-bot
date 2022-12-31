# -*- coding: utf-8 -*-


import jieba
import jieba.analyse


def cut_words_weights(content):
    """
    根据jieba分词，提取关键词及其权重
    :param data:
    :return:
    """
    # jieba提取关键词及其权重
    # 设置停用词
    # jieba.analyse.set_stop_words('path_of_stopwords')
    tags = jieba.analyse.extract_tags(content, topK=20, withWeight=True)
    tags = [(keyword, int(weight * 10)) for keyword, weight in tags]
    return tags


def hash_keyword_add_weight(keyword_weight, len_hash=64):
    """
    对关键词进行hash, 然后加权
    :param keyword_weight:
    :param len_hash:
    :return:
    """
    # 关键词hash
    keyword_weight = [(bin(hash(keyword)).replace("0b", "").replace("-", "").zfill(len_hash)[-1 * len_hash:], weight)
                      for keyword, weight in keyword_weight]
    # 加权
    add_weight = [0] * len_hash
    for keyword, weight in keyword_weight:
        for i in range(len_hash):
            if keyword[i] == "1":
                add_weight[i] += weight
            else:
                add_weight[i] += -1 * weight
    result = ""
    for _ in add_weight:
        if _ >= 0:
            result += "1"
        else:
            result += "0"
    return result


def cal_hamming_distance(hash_file1, hash_file2):
    """
    计算两篇文章的海明距离
    :param hash_file1:
    :param hash_file2:
    :return:
    """
    hamming_dis = 0
    for i in range(len(hash_file1)):
        if hash_file1[i] != hash_file2[i]:
            hamming_dis += 1
    # print("海明距离：", hamming_dis)
    return hamming_dis


class SimHashSimilarity():
    def __init__(self):
        pass

    def run_simhash(self, str1, str2):
        """
        主程序
        :param str1:
        :param str2:
        :return:
        """
        tags1 = cut_words_weights(str1)
        tags2 = cut_words_weights(str2)
        hash_file1 = hash_keyword_add_weight(tags1)
        hash_file2 = hash_keyword_add_weight(tags2)
        hamming_dis = cal_hamming_distance(hash_file1, hash_file2)
        return hamming_dis


if __name__ == "__main__":
    simhash = SimHashSimilarity()
    print(simhash.run_simhash("你妈妈叫你回家吃饭了，小明", "小明的妈妈让你回家吃饭了"))
