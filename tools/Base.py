# -*- coding: utf-8 -*-
# @Time    : 9/22/22 11:04 PM
# @FileName: Base.py
# @Software: PyCharm
# @Github    ：sudoskys

class Tool(object):
    @staticmethod
    def isStrIn(prompt: str, keywords: list, r: float):
        isIn = False
        full = len(keywords)
        score = 0
        for i in keywords:
            if i in prompt:
                score += 1
        if score / full > r:
            isIn = True
        return isIn

    @staticmethod
    def isStrAllIn(prompt: str, keywords: list):
        isIn = True
        for i in keywords:
            if i not in prompt:
                isIn = False
        return isIn
