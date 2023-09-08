import time
from tinydb import TinyDB, Query
from tinydb.operations import increment
from tinydb.table import Document


class RateLimitManager:
    """额度管理器"""

    def __init__(self):
        self.limit_db = TinyDB("data/rate_limit.json")
        self.usage_db = TinyDB("data/rate_usage.json")
        self.draw_limit_db = TinyDB("data/draw_rate_limit.json")
        self.draw_usage_db = TinyDB("data/draw_rate_usage.json")

    def update(self, _type: str, _id: str, rate: int):
        """更新额度限制"""

        q = Query()
        self.limit_db.upsert({"type": _type, "id": _id, "rate": rate}, q.fragment({"type": _type, "id": _id}))

    def update_draw(self, _type: str, _id: str, rate: int):
        """更新画图额度限制"""

        q = Query()
        self.draw_limit_db.upsert({"type": _type, "id": _id, "rate": rate}, q.fragment({"type": _type, "id": _id}))

    def list(self):
        """列出所有的额度限制"""

        return self.limit_db.all()

    def get_limit(self, _type: str, _id: str) -> Document:
        """获取限制"""

        q = Query()
        entity = self.limit_db.get(q.fragment({"type": _type, "id": _id}))
        if entity is None and _id != '默认':
            return self.limit_db.get(q.fragment({"type": _type, "id": '默认'}))
        return entity

    def get_draw_limit(self, _type: str, _id: str) -> Document:
        """获取画图限制"""

        q = Query()
        entity = self.draw_limit_db.get(q.fragment({"type": _type, "id": _id}))
        if entity is None and _id != '默认':
            return self.draw_limit_db.get(q.fragment({"type": _type, "id": '默认'}))
        return entity

    def get_draw_usage(self, _type: str, _id: str) -> Document:
        """获取画图使用量"""

        q = Query()
        usage = self.draw_usage_db.get(q.fragment({"type": _type, "id": _id}))
        current_time = time.localtime(time.time()).tm_hour
        current_day = time.localtime(time.time()).tm_mday

        # 删除过期的记录
        if usage is not None and usage['time'] != current_time:
            self.draw_usage_db.remove(doc_ids=[usage.doc_id])
            usage = None

        # 初始化
        if usage is None:
            usage = {'type': _type, 'id': _id, 'count': 0, 'time': current_time, 'day': current_day}
            self.draw_usage_db.insert(usage)

        return usage

    def get_usage(self, _type: str, _id: str) -> Document:
        """获取使用量"""

        q = Query()
        usage = self.usage_db.get(q.fragment({"type": _type, "id": _id}))
        current_time = time.localtime(time.time()).tm_hour
        current_day = time.localtime(time.time()).tm_mday

        # 删除过期的记录
        time_diff_dondition = (usage is not None and usage['time'] != current_time)
        day_diff_condition = (usage is not None and usage['time'] == current_time and usage['day'] != current_day)
        if time_diff_dondition or day_diff_condition:
            self.usage_db.remove(doc_ids=[usage.doc_id])
            usage = None
            
        # 初始化
        if usage is None:
            usage = {'type': _type, 'id': _id, 'count': 0, 'time': current_time, 'day': current_day}
            self.usage_db.insert(usage)

        return usage

    def increment_usage(self, _type, _id):
        """更新使用量"""

        self.get_usage(_type, _id)

        q = Query()
        self.usage_db.update(increment('count'), q.fragment({"type": _type, "id": _id}))

    def increment_draw_usage(self, _type, _id):
        """更新画图使用量"""

        self.get_usage(_type, _id)

        q = Query()
        self.draw_usage_db.update(increment('count'), q.fragment({"type": _type, "id": _id}))

    def check_exceed(self, _type: str, _id: str) -> float:
        """检查是否超额，返回 使用量/额度"""

        limit = self.get_limit(_type, _id)
        usage = self.get_usage(_type, _id)

        # 此类型下无限制
        if limit is None:
            return 0

        # 此类型下为禁止
        return 1 if limit['rate'] == 0 else usage['count'] / limit['rate']

    def check_draw_exceed(self, _type: str, _id: str) -> float:
        """检查画图是否超额，返回 使用量/额度"""

        limit = self.get_draw_limit(_type, _id)
        usage = self.get_draw_usage(_type, _id)

        # 此类型下无限制
        if limit is None:
            return 0

        # 此类型下为禁止
        return 1 if limit['rate'] == 0 else usage['count'] / limit['rate']