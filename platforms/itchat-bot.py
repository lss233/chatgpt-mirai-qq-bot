# coding=utf-8

# the original code is from https://github.com/why2lyj/youxiang-Itchat/blob/master/chat/wechat.py

import asyncio
import os

# 如果加到bot.py里面，就不需要这两行了
import sys
sys.path.append(os.getcwd())

from loguru import logger

from constants import botManager
from universal import handle_message

import platform
import itchat
from itchat.content import (
    TEXT
)

__all__ = ['run', 'delete_cache']

request_list=[]

async def run():
    """ 主运行入口 """
    try:
        logger.info("OpenAI 服务器登录中……")
        await botManager.login()
    except:
        logger.error("OpenAI 服务器登录失败！")
        exit(-1)

    logger.info("OpenAI 服务器登录成功！")
    logger.info('开始登录...')
    if not is_online(auto_login=True):
        logger.info('程序已退出...')
        return
    
    logger.info('登录成功')
    while True:
        if len(request_list)>0:
            request=request_list.pop(0)
            # logger.info(f"handle request")
            await handle_message(request['response'], request['name'], request['msg'], is_manager=request['is_manager'])
        else:
            # logger.info("no request, sleep 1s")
            await asyncio.sleep(1)


def init_data():
    """ 初始化微信所需数据 """
    itchat.get_friends(update=True)  # 更新好友数据。
    itchat.get_chatrooms(update=True)  # 更新群聊数据。
    logger.info('初始化完成')

def exit_msg():
    """ 退出通知 """
    logger.info('程序已退出')

def is_online(auto_login=False):
    """
    判断是否还在线。
    :param auto_login: bool,当为 Ture 则自动重连(默认为 False)。
    :return: bool,当返回为 True 时，在线；False 已断开连接。
    """

    def _online():
        """
        通过获取好友信息，判断用户是否还在线。
        :return: bool,当返回为 True 时，在线；False 已断开连接。
        """
        try:
            if itchat.search_friends():
                return True
        except IndexError:
            return False
        return True

    if _online(): return True  # 如果在线，则直接返回 True
    if not auto_login:  # 不自动登录，则直接返回 False
        logger.info('微信已离线..')
        return False

    hot_reload = True  # 一段时间内不用再扫码
    login_callback = init_data
    exit_callback = exit_msg
    try:
        for _ in range(2):  # 尝试登录 2 次。
            if platform.system() in ('Windows', 'Darwin'):
                itchat.auto_login(hotReload=hot_reload,
                                  loginCallback=login_callback, exitCallback=exit_callback)
                itchat.run(blockThread=False) # 不让程序阻塞，否则无法调用handle_message。
            else:
                # 命令行显示登录二维码。
                itchat.auto_login(enableCmdQR=2, hotReload=hot_reload, loginCallback=login_callback,
                                  exitCallback=exit_callback)
                itchat.run(blockThread=False)
            if _online():
                logger.info('登录成功')
                return True
    except Exception as exception:  # 登录失败的错误处理。
        sex = str(exception)
        if sex == "'User'":
            logger.exception('此微信号不能登录网页版微信，不能运行此项目。没有任何其它解决办法！可以换个号再试试。')
        else:
            logger.error(sex)

    # delete_cache()  # 清理缓存数据
    logger.info('登录失败。')
    return False


def delete_cache():
    """ 清除缓存数据，避免下次切换账号时出现 """
    file_names = ('QR.png', 'itchat.pkl')
    for file_name in file_names:
        if os.path.exists(file_name):
            os.remove(file_name)    


@itchat.msg_register([TEXT], isFriendChat=True)
def friend_reply(msg):
    """ 监听用户消息，用于自动回复 """
    logger.info(msg.fromUserName+':'+msg.text)
    name = 'friend-' + msg.fromUserName
    is_manager = False
    async def response(msg: str, user = msg.user):
        user.send(msg)

    request={'response':response,'name':name,'msg':msg.text,'is_manager':is_manager}
    request_list.append(request)


@itchat.msg_register([TEXT], isGroupChat=True)
def group_reply(msg):
    """ 监听用户消息，用于自动回复 """
    # logger.info(msg)
    name = 'group-' + msg.fromUserName
    is_manager = False

    async def response(msg: str, itchat_msg = msg):
        if itchat_msg.isAt:
            itchat_msg.user.send(u'@%s\u2005 %s' % (
                itchat_msg.actualNickName, msg))

    request={'response':response,'name':name,'msg':msg.text,'is_manager':is_manager}
    request_list.append(request)

def main():
    asyncio.run(run())


if __name__ == '__main__':
    main()