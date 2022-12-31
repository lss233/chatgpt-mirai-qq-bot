# -*- coding: utf-8 -*-
# @Time    : 12/6/22 6:55 PM
# @FileName: data.py
# @Software: PyCharm
# @Github    ：sudoskys
import ast
import json
from typing import Union

from pydantic import BaseModel

import openai_kira

# 这里是数据基本类

redis_installed = True

try:
    from redis import Redis, ConnectionPool
    from redis import StrictRedis
except Exception as e:
    redis_installed = False

filedb = True
try:
    import elara
except Exception:
    filedb = False

if not filedb and not redis_installed:
    raise Exception("Db/redis all Unusable")


class RedisWorker(object):
    """
    Redis 数据基类
    不想用 redis 可以自动改动此类，换用其他方法。应该比较简单。
    """

    def __init__(self, host='localhost', port=6379, db=0, password=None, prefix='Telecha_'):
        self.redis = ConnectionPool(host=host, port=port, db=db, password=password)

        # self.con = Redis(connection_pool=self.redis) -> use this when necessary
        # {chat_id: {user_id: {'state': None, 'data': {}}, ...}, ...}
        self.prefix = prefix
        if not redis_installed:
            raise Exception("Redis is not installed. Install it via 'pip install redis'")

    def ping(self):
        connection = Redis(connection_pool=self.redis)
        connection.ping()

    def setKey(self, key, obj, exN=None):
        connection = Redis(connection_pool=self.redis)
        connection.set(self.prefix + str(key), json.dumps(obj), ex=exN)
        connection.close()
        return True

    def deleteKey(self, key):
        connection = Redis(connection_pool=self.redis)
        connection.delete(self.prefix + str(key))
        connection.close()
        return True

    def getKey(self, key):
        connection = Redis(connection_pool=self.redis)
        result = connection.get(self.prefix + str(key))
        connection.close()
        if result:
            return json.loads(result)
        else:
            return {}

    def addToList(self, key, listData: list):
        data = self.getKey(key)
        if isinstance(data, str):
            listGet = ast.literal_eval(data)
        else:
            listGet = []
        listGet = listGet + listData
        listGet = list(set(listGet))
        if self.setKey(key, str(listGet)):
            return True

    def getList(self, key):
        listGet = ast.literal_eval(self.getKey(key))
        if not listGet:
            listGet = []
        return listGet


class ElaraWorker(object):
    """
    Redis 数据基类
    不想用 redis 可以自动改动此类，换用其他方法。应该比较简单。
    """

    def __init__(self, filepath, prefix='Openai_'):
        self.redis = elara.exe(filepath)
        self.prefix = prefix
        # self.con = Redis(connection_pool=self.redis) -> use this when necessary
        # {chat_id: {user_id: {'state': None, 'data': {}}, ...}, ...}

    def setKey(self, key, obj):
        self.redis.set(self.prefix + str(key), json.dumps(obj, ensure_ascii=False))
        self.redis.commit()
        return True

    def deleteKey(self, key):
        self.redis.rem(key)
        return True

    def getKey(self, key):
        result = self.redis.get(self.prefix + str(key))
        if result:
            return json.loads(result)
        else:
            return {}

    def addToList(self, key, listData: list):
        data = self.getKey(key)
        if isinstance(data, str):
            listGet = ast.literal_eval(data)
        else:
            listGet = []
        listGet = listGet + listData
        listGet = list(set(listGet))
        if self.setKey(key, str(listGet)):
            return True

    def getList(self, key):
        listGet = ast.literal_eval(self.getKey(key))
        if not listGet:
            listGet = []
        return listGet


class DataUtils(object):
    @staticmethod
    def processString5(txt, ori: str, rep: str, dels: str = None):
        if len(ori) != len(rep):
            raise Exception("NO")
        transTable = txt.maketrans(ori, rep, dels)
        txt = txt.translate(transTable)
        return txt


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None


def GetDataManger(redis_config: RedisConfig, filedb_path: str) -> Union[RedisWorker, ElaraWorker]:
    MsgFlowData = None
    if filedb:
        MsgFlowData = ElaraWorker(filepath=filedb_path)
    if redis_installed:
        try:
            MsgFlowData_ = RedisWorker(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                prefix="Open_Ai_memory_chat_r_")
            MsgFlowData_.ping()
        except Exception as e:
            pass
        else:
            MsgFlowData = MsgFlowData_
    return MsgFlowData


class MsgFlow(object):
    """
    数据存储桶，用于上下文分析时候提取桶的内容
    """

    def __init__(self, uid):
        """
        消息流存储器
        :param uid: 独立 id ，是一个消息桶
        """
        self.uid = str(uid)
        _redis_config = openai_kira.redis
        # 工具数据类型
        self.MsgFlowData = GetDataManger(_redis_config, openai_kira.filedb)
        self.memory: int = 100

    @staticmethod
    def composing_uid(user_id, chat_id):
        return f"{user_id}:{chat_id}"

    def _get_uid(self, uid):
        return self.MsgFlowData.getKey(uid)

    def _set_uid(self, uid, message_streams):
        return self.MsgFlowData.setKey(uid, message_streams)

    def get_content(self, meo, sign: bool = False) -> tuple:
        """
        得到单条消息的内容
        :param sign: 是否署名
        :param meo: 消息对象提取内容
        :return: ask,reply
        """
        _ask_ = meo["content"].get("ask")
        _reply_ = meo["content"].get("reply")
        if not sign and ":" in _ask_ and '：' in _reply_:
            _ask_ = _ask_.split(":", 1)[1]
            _reply_ = _reply_.split(":", 1)[1]
        return _ask_, _reply_

    def saveMsg(self, msg: dict) -> None:
        # {"ask": {self._restart_sequence: prompt}, "reply": {self._start_sequence: REPLY[0]}}
        import time
        time_s = int(time.time() * 1000)
        content = {"content": msg, "time": time_s}
        _message_streams = self._get_uid(self.uid)
        if "msg" in _message_streams:
            _message_streams["msg"] = sorted(_message_streams["msg"], key=lambda x: x['time'], reverse=False)
            # 记忆容量重整
            if len(_message_streams["msg"]) > self.memory:
                for i in range(len(_message_streams["msg"]) - self.memory + 1):
                    # 多弹出一个用于腾出容量，不能在前面弹出，会造成无法记忆的情况！
                    _message_streams["msg"].pop(0)
            _message_streams["msg"].append(content)
        else:
            _message_streams["msg"] = [content]
        self._set_uid(self.uid, _message_streams)

    def read(self) -> list:
        message_streams = self._get_uid(self.uid)
        if "msg" in message_streams:
            _msg = message_streams["msg"]
            return _msg
        else:
            return []

    def forget(self):
        _message_streams = self._get_uid(self.uid)
        if "msg" in _message_streams:
            _message_streams["msg"] = []
            self._set_uid(self.uid, _message_streams)
        return True
