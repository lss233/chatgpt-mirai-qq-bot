import time
from tinydb import TinyDB, Query
from tinydb.operations import increment
class RateLimitManager:
    """额度管理器"""

    def __init__(self):
        self.limit_db = TinyDB("data/rate_limit.json")
        self.usage_db = TinyDB("data/rate_usage.json")
    
    def update(self, type: str, id: str, rate: int):
        """更新额度限制"""

        q = Query()
        self.limit_db.upsert({"type": type, "id": id, "rate": rate}, q.fragment({"type": type, "id": id}))

    def list(self):
        """列出所有的额度限制"""

        return self.limit_db.all()

    def get_limit(self, type: str, id: str):
        """获取限制"""

        q = Query()
        entity = self.limit_db.get(q.fragment({"type": type, "id": id}))
        if entity is None and not id == '默认':
            return self.limit_db.get(q.type == type and q.id == '默认')
        return entity
        
    def get_usage(self, type: str, id: str):
        """获取使用量"""

        q = Query()
        usage = self.usage_db.get(q.fragment({"type": type, "id": id}))
        current_time = time.localtime(time.time()).tm_hour

        # 删除过期的记录
        if usage is not None and usage['time'] != current_time:
            self.usage_db.remove(usage)
            usage = None
        
        # 初始化
        if usage is None:
            usage = {'type': type, 'id': id, 'count': 0, 'time': current_time}
            self.usage_db.insert(usage)
        
        return usage

    def increment_usage(self, type, id):
        """更新使用量"""

        self.get_usage(type, id)

        q = Query()
        self.usage_db.update(increment('count'), q.fragment({"type": type, "id": id}))

    def check_exceed(self, type: str, id: str) -> float:
        """检查是否超额，返回 使用量/额度"""

        limit = self.get_limit(type, id)
        usage = self.get_usage(type, id)

        # 此类型下无限制
        if limit is None:
            return 0

        # 此类型下为禁止
        if limit['rate'] == 0:
            return 1

        return usage['count'] / limit['rate']