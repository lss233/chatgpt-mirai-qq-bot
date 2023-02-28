"""本文件用于管理多账号下各用户的会话"""
"""需要注意的是，存储所有用户对话信息的session_records字典单独存储在一个文件，并映射到本地，这样即使容器重装、更新等也能读取之前的对话"""

# session_records样例如下：
"""
session_records = {
    "user1": {
        "max_sessions": 5,  # 用户1最多允许5个会话记录
        "sessions": [#记录user1的不同会话
            {
                "conversation_id": "conv1",
                "session_id": "fd-123-对话1"
                "account_id": "account_1"
                "parent_ids": ["parent1", "parent2"],
            },
            {
                "conversation_id": "conv2",
                "session_id": "fd-123-对话2"
                "account_id": "account_2"
                "parent_ids": ["parent3"],
            },
            # ... 更多的会话记录
        ],
    },
    "user2": {
        "max_sessions": 10,  # 用户2最多允许10个会话记录
        "sessions": [#记录user1的不同会话
            {
                "conversation_id": "conv1",
                "session_id": "fd-123-对话1"
                "account_id": "account_1"
                "parent_ids": ["parent1", "parent2"],
            },
            {
                "conversation_id": "conv2",
                "session_id": "fd-123-对话2"
                "account_id": "account_2"
                "parent_ids": ["parent3"],
            },
            # ... 更多的会话记录
        ],
    },
    # ... 更多的用户
}
"""

from config import Config, OpenAIAuths
from tinydb import TinyDB, Query

config = Config.load_config()


# 添加对话记录
def add_session_record(user_id, conversation_id, session_id, account_id, parent_id):
    if conversation_id == None:
        return

    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        session_records[user_id] = {
            "max_sessions": 5,
            "sessions": [],
        }

    # 检查新会话记录是否已经存在于会话记录列表中
    record_found = False
    for record in session_records[user_id]["sessions"]:
        if record["conversation_id"] == conversation_id:
            if record["parent_ids"][-1] != parent_id:
                record["parent_ids"].append(parent_id)
            record_found = True
            break

    # 如果新会话记录不存在，则添加新的会话记录
    if not record_found:
        # 检查用户会话记录是否已经达到最大数量
        if len(session_records[user_id]["sessions"]) >= session_records[user_id]["max_sessions"]:
            # 删除第一个会话记录，并将新记录插入到末尾
            session_records[user_id]["sessions"].pop(0)

        new_record = {
            "conversation_id": conversation_id,
            "session_id": session_id,
            "account_id": account_id,
            "parent_ids": [parent_id],
        }
        session_records[user_id]["sessions"].append(new_record)

    # 保存session_records字典
    # with open('session_records.json', 'w') as f:
    #     f.write(json.dumps(session_records))
    # 完全替代原有数据表的内容
    table.write_back = True
    table.truncate()  # 清空数据表
    table.insert(session_records)
    # 关闭数据库
    db.close()
    # return session_records  # 返回更新后的会话记录字典


# 返回指定用户的会话列表，返回样例：[session_id1, session_id2...]
def get_user_sessions(user_id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        return []  # 用户不存在，返回空列表

    # 获取用户的会话列表
    sessions = session_records[user_id]["sessions"]

    # 提取会话ID和会话记录ID，生成一个嵌套列表
    result = [session["session_id"] for session in sessions]

    return result  # 返回用户的会话列表


# 返回指定会话最后一个[conversation_id, parent_ids, account_id]
def get_last_parent_id(user_id, id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        return None  # 用户不存在，返回None

    # 获取用户的会话列表
    sessions = session_records[user_id]["sessions"]

    # 查找指定会话的会话记录
    record_found = False
    if id > 0 and id <= len(sessions):
        record_found = True

    # 如果找到了指定会话的会话记录，则返回最后一个parent_id
    if record_found:
        if len(sessions[id - 1]["parent_ids"]) > 0:
            # session_records[user_id]["sessions"][id - 1]["parent_ids"].pop()
            # 保存session_records字典
            # with open('session_records.json', 'w') as f:
            #     f.write(json.dumps(session_records))
            # 完全替代原有数据表的内容
            # table.write_back = True
            # table.truncate()  # 清空数据表
            # table.insert(session_records)
            # 关闭数据库
            # db.close()

            return [sessions[id - 1]["conversation_id"], sessions[id - 1]["parent_ids"], sessions[id - 1]["account_id"]]
        else:
            return None  # 如果parent_ids列表为空，则返回None
    else:
        return None  # 如果没有找到指定会话的会话记录，则返回None


# 删除指定会话
def delete_session_record(user_id, id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        return None  # 用户不存在，直接返回None

    # 获取用户的会话列表
    sessions = session_records[user_id]["sessions"]

    # 查找指定会话的会话记录
    record_found = False
    last_record = False
    if id > 0 and id <= len(sessions):
        if id == len(sessions):
            last_record = True
        session_records[user_id]["sessions"].pop(id - 1)
        record_found = True

    # 如果找到了指定会话的会话记录，则返回更新后的会话记录字典
    if record_found:
        # 保存session_records字典
        # with open('session_records.json', 'w') as f:
        #     f.write(json.dumps(session_records))
        # 完全替代原有数据表的内容
        table.write_back = True
        table.truncate()  # 清空数据表
        table.insert(session_records)
        # 关闭数据库
        db.close()

        if last_record:  # 如果删除的恰巧是最后一个，也就是当前会话
            return 2
        return 1
    else:
        return None  # 如果没有找到指定会话的会话记录，则直接返回None


# 清空指定用户所有会话
def clear_user_sessions(user_id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        return None  # 用户不存在，直接返回会话记录字典

    # 删除指定用户的所有会话记录
    session_records[user_id]["sessions"] = []

    # 保存session_records字典
    # with open('session_records.json', 'w') as f:
    #     f.write(json.dumps(session_records))
    # 完全替代原有数据表的内容
    table.write_back = True
    table.truncate()  # 清空数据表
    table.insert(session_records)
    # 关闭数据库
    db.close()

    return True


# 回滚会话,返回parent_id，否则返回None
def rollback_last_parent_id(user_id, conversation_id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 检查用户是否存在
    if user_id not in session_records:
        return None  # 用户不存在，返回None

    # 获取用户的会话列表
    sessions = session_records[user_id]["sessions"]

    # 查找指定会话的会话记录
    record_found = False
    for session in sessions:
        if session["conversation_id"] == conversation_id:
            record_found = True
            break

    # 如果找到了指定会话的会话记录，则回滚最后一个parent_id
    if record_found:
        parent_ids = session["parent_ids"]
        if len(parent_ids) > 0:
            parent_ids.pop(-1)

            # 保存session_records字典
            # with open('session_records.json', 'w') as f:
            #     f.write(json.dumps(session_records))
            # 完全替代原有数据表的内容
            table.write_back = True
            table.truncate()  # 清空数据表
            table.insert(session_records)
            # 关闭数据库
            db.close()

            if len(parent_ids) > 0:
                return parent_ids[-1]  # 如果还有剩余的parent_id，则返回新的最后一个parent_id
            else:
                return None  # 如果parent_ids列表为空，则返回None
        else:
            return None  # 如果parent_ids列表为空，则返回None
    else:
        return None  # 如果没有找到指定会话的会话记录，则返回None


# 更新指定用户指定会话的会话名
def update_session(user_id, conversation_id, session_id):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    if user_id not in session_records:
        # 如果用户不存在，则返回None
        return None

    for i in range(len(session_records[user_id]["sessions"])):
        if session_records[user_id]["sessions"][i]["conversation_id"] == conversation_id:
            # 找到会话，更新session_id
            session_records[user_id]["sessions"][i]["session_id"] = session_id
            # 保存session_records字典
            # with open('session_records.json', 'w') as f:
            #     f.write(json.dumps(session_records))
            # 完全替代原有数据表的内容
            table.write_back = True
            table.truncate()  # 清空数据表
            table.insert(session_records)
            # 关闭数据库
            db.close()

            return

        # 修改指定用户的会话上限


def update_max_sessions(user_id, max_sessions):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    if max_sessions > config.max_record.max_sessions:
        max_sessions = config.max_record.max_sessions
    elif max_sessions < 1:
        max_sessions = 1

    if user_id in session_records:
        session_records[user_id]["max_sessions"] = max_sessions
    else:
        session_records[user_id] = {"max_sessions": max_sessions, "sessions": []}

    while max_sessions < len(session_records[user_id]["sessions"]):
        session_records[user_id]["sessions"].pop(0)

    # 保存session_records字典
    # with open('session_records.json', 'w') as f:
    #     f.write(json.dumps(session_records))
    # 完全替代原有数据表的内容
    table.write_back = True
    table.truncate()  # 清空数据表
    table.insert(session_records)
    # 关闭数据库
    db.close()


# 更新account_id（session_token登录的用户补上了email）
def update_account_id(account_id_before, account_id_after):
    # 打开数据库
    db = TinyDB('data/session_records.json')

    # 获取数据表
    table = db.table('session_records')

    # 读取数据
    session_records = table.all()
    if len(session_records) > 0:
        session_records = session_records[0]
    else:
        session_records = {}
    # 读取session_records字典
    # with open('session_records.json', 'r') as f:
    #     session_records = json.loads(f.read())

    # 遍历所有用户的会话记录
    for user in session_records:
        for session in session_records[user]["sessions"]:
            # 如果会话记录中包含原始的account_id，则将其替换为新的account_id
            if session["account_id"] == account_id_before:
                session["account_id"] = account_id_after

    # 保存session_records字典
    # with open('session_records.json', 'w') as f:
    #     f.write(json.dumps(session_records))
    # 完全替代原有数据表的内容
    table.write_back = True
    table.truncate()  # 清空数据表
    table.insert(session_records)
    # 关闭数据库
    db.close()
