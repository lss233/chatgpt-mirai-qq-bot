# -*- coding: utf-8 -*-
# @Time    : 12/27/22 6:12 PM
# @FileName: web.py
# @Software: PyCharm
# @Github    ：sudoskys
import os

__all__ = [f.strip(".py") for f in os.listdir(os.path.abspath(os.path.dirname(__file__))) if
           f.endswith('.py') and "_" not in f]

# print(__all__)


if __name__ == '__main__':
    s = [f.strip(".py") for f in os.listdir('.') if f.endswith('.py') and "_" not in f]
    print(s)
