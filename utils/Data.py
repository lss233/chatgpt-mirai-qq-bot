# -*- coding: utf-8 -*-
# @Time    : 12/5/22 5:59 PM
# @FileName: DataWorker.py
# @Software: PyCharm
# @Github    ：sudoskys
import pathlib
# 缓冲
from collections import OrderedDict
from datetime import datetime, timedelta

from loguru import logger
from pydantic import BaseModel

# -*- coding: utf-8 -*-
# @Time    : 12/6/22 6:55 PM
# @FileName: data.py
# @Software: PyCharm
# @Github    ：sudoskys
import ast
import json
from typing import Union

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


class Usage_Data(BaseModel):
    user: str
    now: int
    usage: int
    total_usage: int


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None


class DefaultData(object):
    """
    数据提供类
    """

    @staticmethod
    def composing_uid(user_id, chat_id):
        # return f"{user_id}:{chat_id}"
        return f"{user_id}"

    @staticmethod
    def mask_middle(s: str, n: int) -> str:
        # 计算需要替换的字符数
        num_chars = len(s) - 2 * n
        # 构造替换字符串
        mask = "*" * num_chars
        # 将替换字符串插入到原字符串的指定位置
        return s[:n] + mask + s[n + num_chars:]

    @staticmethod
    def defaultConfig():
        return {
            "statu": True,
            "input_limit": 250,
            "token_limit": 300,
            "hour_limit": 15000,
            "per_user_limit": 1,
            "usercold_time": 10,
            "groupcold_time": 1,
            "User": {},
            "Group": {},
            "whiteUserSwitch": True,
            "whiteGroupSwitch": True,
            "Model": {
            },
            "allow_change_head": True
        }

    @staticmethod
    def defaultKeys():
        return {"OPENAI_API_KEY": []}

    @staticmethod
    def defaultAnalysis():
        return {"frequency": 0, "usage": {}}

    def setAnalysis(self,
                    **kwargs
                    ):
        """
        frequency,
        usage,
        :param self:
        :param kwargs:
        :return:
        """
        _Analysis = self.defaultAnalysis()
        if pathlib.Path("./analysis.json").exists():
            with open("./analysis.json", encoding="utf-8") as f:
                DictUpdate.dict_update(_Analysis, json.load(f))
        DictUpdate.dict_update(_Analysis, kwargs)
        with open("./analysis.json", "w+", encoding="utf8") as f:
            json.dump(_Analysis, f, indent=4, ensure_ascii=False)

    @staticmethod
    def defaultUser():
        return {"white": False,
                "block": False,
                "usage": 1,
                "voice": False
                }

    # 单独配额，如果这里不是 1,优先按这这分配额度
    @staticmethod
    def defaultGroup():
        return {
            "white": False,
            "block": False
        }

    @staticmethod
    def defaultService():
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None
            },
            "plugin": {
            },
            "tts": {
                "status": True,
                "type": "none",
                "vits": {
                    "api": "http://127.0.0.1:9557/tts/generate",
                    "limit": 70,
                    "model_name": "some.pth",
                    "speaker_id": 0
                },
                "azure": {
                    "key": [""],
                    "limit": 70,
                    "speaker": {
                        "chinese": "zh-CN-XiaoxiaoNeural"
                    },
                    "location": "japanwest"
                }
            }
        }


class Service_Data(object):
    """
    管理 Api
    """

    @staticmethod
    def get_key(filePath: str = "./Config/service.json"):
        now_table = DefaultData.defaultService()
        if pathlib.Path(filePath).exists():
            with open(filePath, encoding="utf-8") as f:
                _config = json.load(f)
                DictUpdate.dict_update(now_table, _config)
                _config = now_table
            return _config
        else:
            return now_table

    @staticmethod
    def save_key(_config, filePath: str = "./Config/service.json"):
        with open(filePath, "w+", encoding="utf8") as f:
            json.dump(_config, f, indent=4, ensure_ascii=False)


class Api_keys(object):
    """
    管理 Api
    """

    @staticmethod
    def get_key(filePath: str = "./Config/api_keys.json"):
        now_table = DefaultData.defaultKeys()
        if pathlib.Path(filePath).exists():
            with open(filePath, encoding="utf-8") as f:
                _config = json.load(f)
                DictUpdate.dict_update(now_table, _config)
                _config = now_table
            return _config
        else:
            return now_table

    @staticmethod
    def save_key(_config, filePath: str = "./Config/api_keys.json"):
        with open(filePath, "w+", encoding="utf8") as f:
            json.dump(_config, f, indent=4, ensure_ascii=False)

    @staticmethod
    def add_key(key: str, filePath: str = "./Config/api_keys.json"):
        _config = Api_keys.get_key()
        _config['OPENAI_API_KEY'].append(key)
        _config["OPENAI_API_KEY"] = list(set(_config["OPENAI_API_KEY"]))
        with open(filePath, "w", encoding="utf8") as f:
            json.dump(_config, f, indent=4, ensure_ascii=False)
        return key

    @staticmethod
    def pop_key(key: str, filePath: str = "./Config/api_keys.json"):
        _config = Api_keys.get_key()
        if key not in _config['OPENAI_API_KEY']:
            return
        _config['OPENAI_API_KEY'].remove(key)
        _config["OPENAI_API_KEY"] = list(set(_config["OPENAI_API_KEY"]))
        with open(filePath, "w", encoding="utf8") as f:
            json.dump(_config, f, indent=4, ensure_ascii=False)
        return key

    @staticmethod
    def pop_api_key(resp, auth):
        # 读取
        _config = Api_keys.get_key()
        _config: dict
        # 弹出
        ERROR = resp.get("error")
        if ERROR:
            if ERROR.get('type') == "insufficient_quota":
                if isinstance(_config["OPENAI_API_KEY"], list) and auth in _config["OPENAI_API_KEY"]:
                    _config["OPENAI_API_KEY"].remove(auth)
                    logger.error(
                        f"弹出过期ApiKey:  --type insufficient_quota --auth {DefaultData.mask_middle(auth, 4)}")
                    # 存储
            if ERROR.get('code') == "invalid_api_key":
                if isinstance(_config["OPENAI_API_KEY"], list) and auth in _config["OPENAI_API_KEY"]:
                    _config["OPENAI_API_KEY"].remove(auth)
                    logger.error(f"弹出非法ApiKey: --type invalid_api_key --auth {DefaultData.mask_middle(auth, 4)}")
        Api_keys.save_key(_config)




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


class DictUpdate(object):
    """
    字典深度更新
    """

    @staticmethod
    def dict_update(raw, new):
        DictUpdate.dict_update_iter(raw, new)
        DictUpdate.dict_add(raw, new)

    @staticmethod
    def dict_update_iter(raw, new):
        for key in raw:
            if key not in new.keys():
                continue
            if isinstance(raw[key], dict) and isinstance(new[key], dict):
                DictUpdate.dict_update(raw[key], new[key])
            else:
                raw[key] = new[key]

    @staticmethod
    def dict_add(raw, new):
        update_dict = {}
        for key in new:
            if key not in raw.keys():
                update_dict[key] = new[key]
        raw.update(update_dict)


def getPuffix(self, fix):
    connection = Redis(connection_pool=self.redis)
    listGet = connection.scan_iter(f"{fix}*")
    connection.close()
    return listGet


def limit_dict_size(dicts, max_size):
    if len(dicts) > max_size:
        # 如果字典中的键数量超过了最大值，则删除一些旧的键
        dicts = dicts[max_size:]
    return dicts
