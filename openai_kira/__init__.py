# -*- coding: utf-8 -*-
# @Time    : 12/5/22 9:54 PM
# @FileName: __init__.py
# @Software: PyCharm
# @Github    ：sudoskys
from pydantic import BaseModel

from .resouce import Completion
from .Chat import Chatbot


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None


redis = RedisConfig()
filedb = "openai_msg.db"
api_key = None
proxy_url = ""
webServerUrlFilter = False
webServerStopSentence = ["下面就让我们",
                         "小编", "一起来看一下", "小伙伴们",
                         "究竟是什么意思", "看影片", "看人次", "？", "是什么", "什么意思", "意思介绍", " › ",
                         "游侠", "为您提供", "今日推荐", "線上看", "线上看",
                         "高清观看", "点击下载", "带来不一样的", "..去看看",
                         "最新章节", "电影网", "资源下载：", "高清全集在线",
                         "在线观看地址"]  # "?","_哔哩哔哩_bilibili","知乎",
