import os, sys
sys.path.append(os.getcwd())

from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import (
    HttpClientConfig,
    WebsocketClientConfig,
    config,
)
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.base import MentionMe
from graia.ariadne.message.element import Plain, Image
from graia.ariadne.model import Friend, Group, Member
import chatbot
import asyncio, functools
import contextvars
import json
from text_to_img import text_to_image
from io import BytesIO

# Polyfill for Python < 3.9
async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)
if not hasattr(asyncio, 'to_thread'):
    asyncio.to_thread = to_thread
with open("config.json", "r") as jsonfile:
    config_data = json.load(jsonfile)

# Refer to https://graia.readthedocs.io/ariadne/quickstart/
app = Ariadne(
    config(
        config_data["mirai"]["qq"],  # 你的机器人的 qq 号
        config_data["mirai"]["api_key"],  # 填入 VerifyKey
        HttpClientConfig(host=config_data["mirai"]["http_url"]),
        WebsocketClientConfig(host=config_data["mirai"]["ws_url"]),
    ),
)

def handle_message(id, message):
    if message.strip() == '':
        return "您好！我是 Assistant，一个由 OpenAI 训练的大型语言模型。我不是真正的人，而是一个计算机程序，可以通过文本聊天来帮助您解决问题。如果您有任何问题，请随时告诉我，我将尽力回答。\n如果您需要重置我们的会话，请回复`重置会话`。"
    bot = chatbot.bot
    session = chatbot.get_chat_session(id)
    if message.strip() == '重置会话':
        session.reset_conversation()
        return "会话已重置。"
    if message.strip() == '回滚对话':
        if session.rollback_conversation():
            return "已回滚至上一条对话，你刚刚发的我就忘记啦！"
        else:
            return "回滚失败，没有更早的记录了！"
    try:
        resp = session.get_chat_response(message)
        print(id, resp)
        return resp["message"]
    except Exception as e:
        # session.reset_conversation()
        bot.refresh_session()
        return '出现故障！如果这个问题持续出现，请和我说“重置会话” 来开启一段新的会话，或者发送 “回滚对话” 来回溯到上一条对话，你上一条说的我就当作没看见。\n' + str(e)

@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend, chain: MessageChain):
    if friend.id == config_data['mirai']['qq']:
        return
    response = await asyncio.to_thread(handle_message, id=f"friend-{friend.id}", message=chain.display)
    await app.send_message(friend, response)

@app.broadcast.receiver("GroupMessage", decorators=[MentionMe()])
async def on_mention_me(group: Group, member: Member, chain: MessageChain = MentionMe()):
    response = await asyncio.to_thread(handle_message, id=f"group-{group.id}", message=chain.display)
    event = await app.send_message(group,  response)
    if(event.source.id < 0):
        img = text_to_image(text=response)
        b = BytesIO()
        img.save(b, format="png")
        await app.send_message(group, Image(data_bytes=b.getvalue()))

app.launch_blocking()
