# -*- coding: utf-8 -*-
# @Time    : 12/31/22 3:51 PM
# @FileName: chatopenai.py
# @Software: PyCharm
# @Github    ：sudoskys
import time

from revChatGPT.ChatGPT import Chatbot
from charset_normalizer import from_bytes
from typing import Awaitable, Any, Dict, Tuple, Union

import openai_kira
from config import Config
from loguru import logger
import json
import os, sys
import asyncio
import uuid

# Kira
import random
import pathlib
from tools.Chat import Utils, Usage, Header, rqParser
from tools.Data import DefaultData
from tools.Detect import Censor, DFA

urlForm = {
    "Danger.form": [
        "https://raw.githubusercontent.com/fwwdn/sensitive-stop-words/master/%E6%94%BF%E6%B2%BB%E7%B1%BB.txt",
        "https://raw.githubusercontent.com/TelechaBot/AntiSpam/main/Danger.txt"
    ]
}


def InitCensor():
    return Censor.InitWords(url=urlForm, home_dir="./Config/")


if not pathlib.Path("./Config/Danger.form").exists():
    InitCensor()
# 过滤器
ContentDfa = DFA(path="./Config/Danger.form")

# from tools.Data import Api_keys
# 因为架构不同不能使用这个 api key 管理器

with open("config.json", "rb") as f:
    guessed_json = from_bytes(f.read()).best()
    if not guessed_json:
        raise ValueError("无法识别 JSON 格式")

    config = Config.parse_obj(json.loads(str(guessed_json)))

try:
    bot = Chatbot(config=config.openai.dict(exclude_none=True, by_alias=False), conversation_id=None)
    logger.debug(f"获取 api key {bot.config['api_key']}")
    # 校验 Key 格式
    for it in bot.config['api_key']:
        it: str
        if not it.startswith("sk-"):
            raise Exception("配置了非法的 Api Key")

except Exception as e:
    logger.exception(e)
    exit(-1)


class ChatUtils(object):
    """
    群组
    """

    @staticmethod
    async def load_response(user,
                            group,
                            key: Union[str, list],
                            prompt: str = "Say this is a test",
                            usercoldtime: int = 1,
                            groupcoldtime: int = 1,
                            method: str = "chat",
                            start_name: str = "Ai:",
                            restart_name: str = "Human:",
                            input_limit: int = 100
                            ):
        """
        发起请求
        :param usercoldtime: 用户冷却时间
        :param groupcoldtime: 群组冷却时间
        :param input_limit:输入限制
        :param start_name: Ai称呼自己
        :param restart_name: Ai称呼用户
        :param user:用户ID
        :param group:聊天组ID
        :param key:api key
        :param prompt:输入内容
        :param method:方法，chat 之类的
        :return:
        """
        if not key:
            logger.error("SETTING:API key missing")
            raise Exception("API key missing")
        # 长度限定
        if input_limit < len(str(prompt)) / 4:
            return "TOO LONG"
        # 内容审计
        if ContentDfa.exists(str(prompt)):
            _censor_child = ["你说啥呢？", "我不说,", "不懂年轻人,", "6 ", "6666 ", "我不好说，", "害怕，",
                             "这是理所当然的，",
                             "我可以说的是……", "我想说的是……", "我想强调的是……", "我想补充的是……", "我想指出的是……",
                             "我想重申的是……", "我想强调的是……""什么事儿呀，", "是啊，是啊。", "你猜啊，", "就是啊，",
                             "哎呀，真的吗？",
                             "啊哈哈哈。", "你知道的。"]
            _censor = ["有点离谱，不想回答", "累了，歇会儿", "能不能换个话题？", "我不想说话。", "没什么好说的。",
                       "现在不是说话的时候。", "我没有什么可说的。", "我不喜欢说话。",
                       "我不想接受问题。", "我不喜欢被问问题。", "我觉得这个问题并不重要。", "我不想谈论这个话题。",
                       "我不想对这个问题发表意见。"]
            _info = f"{random.choice(_censor_child)} {random.choice(_censor)} --"
            return _info
        # 洪水防御攻击
        if Utils.WaitFlood(user=user, group=group, groupcold_time=groupcoldtime, usercold_time=usercoldtime):
            return "TOO FAST"
        # 用量检测
        _UsageManger = Usage(uid=user)
        _Usage = _UsageManger.isOutUsage()
        if _Usage["status"]:
            return f"小时额度或者单人总额度用完，请申请重置或等待\n{_Usage['use']}"
        # 请求
        try:
            # import openai_kira
            openai_kira.api_key = key
            if method == "chat":
                # CHAT
                from openai_kira import Chat
                _cid = DefaultData.composing_uid(user_id=user, chat_id=group)
                # 启用单人账户桶
                if len(start_name) > 12:
                    start_name = start_name[-10:]
                if len(restart_name) > 12:
                    restart_name = restart_name[-10:]
                receiver = Chat.Chatbot(
                    conversation_id=int(_cid),
                    call_func=None,  # Api_keys.pop_api_key,
                    start_sequ=start_name,
                    restart_sequ=restart_name,
                )
                _head = Header(uid=user).get()
                if _head:
                    _head = ContentDfa.filter_all(_head)
                response = await receiver.get_chat_response(model="text-davinci-003",
                                                            prompt=str(prompt),
                                                            max_tokens=bot.config['token_limit'],
                                                            role=_head,
                                                            web_enhance_server=bot.config['plugin'],
                                                            )
            else:
                return "NO SUPPORT METHOD"
            # print(response)
            _deal_rq = rqParser.get_response_text(response)
            # print(_deal_rq)
            _deal = _deal_rq[0]
            _usage = rqParser.get_response_usage(response)
            _time = int(time.time() * 1000)
            logger.success(f"CHAT:{user}:{group} --time: {_time} --prompt: {prompt} --req: {_deal} ")
        except Exception as e:
            logger.error(f"RUN:Api Error:{e}")
            _usage = 0
            _deal = f"Api Outline or too long prompt \n {prompt}"
        # 更新额度
        _AnalysisUsage = _UsageManger.renewUsage(usage=_usage)
        # 统计
        DefaultData().setAnalysis(usage={f"{user}": _AnalysisUsage.total_usage})
        _deal = ContentDfa.filter_all(_deal)
        # 人性化处理
        _deal = Utils.Humanization(_deal)
        return _deal


class ChatSession:
    def __init__(self):
        self.reset_conversation()

    def reset_conversation(self, conversation_id: str):
        """
        重置消息流
        :return:
        """
        from openai_kira.utils.data import MsgFlow
        _cid = conversation_id
        return MsgFlow(uid=_cid).forget()

    def rollback_conversation(self, conversation_id: str) -> bool:
        from openai_kira.utils.data import MsgFlow
        _cid = conversation_id
        MsgFlow(uid=_cid).forget()
        # if len(self.prev_parent_id) <= 0:
        #     return False
        # self.conversation_id = self.prev_conversation_id.pop()
        # self.parent_id = self.prev_parent_id.pop()
        return True

    async def get_chat_response(self, message) -> Tuple[Dict[str, Any], Exception]:
        self.prev_conversation_id.append(self.conversation_id)
        self.prev_parent_id.append(self.parent_id)
        bot.conversation_id = self.conversation_id
        bot.parent_id = self.parent_id
        final_resp = None
        exception = None
        try:
            final_resp = bot.ask(message)
            self.conversation_id = final_resp["conversation_id"]
            self.parent_id = final_resp["parent_id"]
        except Exception as e:
            exception = e
        return final_resp, exception


sessions = {}


def get_chat_session(id: str) -> ChatSession:
    if id not in sessions:
        sessions[id] = ChatSession()
    return sessions[id]
