# -*- coding: utf-8 -*-
# @Time    : 12/15/22 11:23 AM
# @FileName: api.py
# @Software: PyCharm
# @Github    ：sudoskys
import json
import os


def load_api():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), ".", "api_url.json")
    )
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            return json.loads(f.read())
    else:
        raise FileNotFoundError("NotFind:api_url.json")
