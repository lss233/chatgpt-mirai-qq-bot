# 定义优雅退出异常
import asyncio

shutdown_event = asyncio.Event()

restart_flag = False


def set_restart_flag():
    global restart_flag
    restart_flag = True

def get_and_reset_restart_flag():
    global restart_flag
    flag = restart_flag
    restart_flag = False
    return flag


