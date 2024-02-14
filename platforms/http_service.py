import json
import threading
import time
import asyncio
import re

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Voice
from graia.ariadne.message.element import Plain
from loguru import logger
from quart import Quart, request

from constants import config, BotPlatform
from universal import handle_message

from urllib.parse import unquote

app = Quart(__name__)

lock = threading.Lock()

request_dic = {}

RESPONSE_SUCCESS = "SUCCESS"
RESPONSE_FAILED = "FAILED"
RESPONSE_DONE = "DONE"


class BotRequest:
    def __init__(self, session_id, username, message, request_time):
        self.session_id: str = session_id
        self.username: str = username
        self.message: str = message
        self.result: ResponseResult = ResponseResult()
        self.request_time = request_time
        self.done: bool = False
        """请求是否处理完毕"""

    def set_result_status(self, result_status):
        if not self.result:
            self.result = ResponseResult()
        self.result.result_status = result_status

    def append_result(self, result_type, result):
        with lock:
            if result_type == "message":
                self.result.message.append(result)
            elif result_type == "voice":
                self.result.voice.append(result)
            elif result_type == "image":
                self.result.image.append(result)


class ResponseResult:
    def __init__(self, message=None, voice=None, image=None, result_status=RESPONSE_SUCCESS):
        self.result_status = result_status
        self.message = self._ensure_list(message)
        self.voice = self._ensure_list(voice)
        self.image = self._ensure_list(image)

    def _ensure_list(self, value):
        if value is None:
            return []
        elif isinstance(value, list):
            return value
        else:
            return [value]

    def is_empty(self):
        return not self.message and not self.voice and not self.image

    def pop_all(self):
        with lock:
            self.message = []
            self.voice = []
            self.image = []

    def to_json(self):
        return json.dumps({
            'result': self.result_status,
            'message': self.message,
            'voice': self.voice,
            'image': self.image
        })


async def process_request(bot_request: BotRequest):
    async def response(msg):
        logger.info(f"Got response msg -> {type(msg)} -> {msg}")
        _resp = msg
        if not isinstance(msg, MessageChain):
            _resp = MessageChain(msg)
        for ele in _resp:
            if isinstance(ele, Plain) and str(ele):
                bot_request.append_result("message", str(ele))
            elif isinstance(ele, Image):
                bot_request.append_result("image", f"data:image/png;base64,{ele.base64}")
            elif isinstance(ele, Voice):
                # mp3
                bot_request.append_result("voice", f"data:audio/mpeg;base64,{ele.base64}")
            else:
                logger.warning(f"Unsupported message -> {type(ele)} -> {str(ele)}")
                bot_request.append_result("message", str(ele))
    logger.debug(f"Start to process bot request {bot_request.request_time}.")
    if bot_request.message is None or not str(bot_request.message).strip():
        await response("message 不能为空!")
        bot_request.set_result_status(RESPONSE_FAILED)
    else:
        await handle_message(
            response,
            bot_request.session_id,
            bot_request.message,
            nickname=bot_request.username,
            request_from=BotPlatform.HttpService
        )
        bot_request.set_result_status(RESPONSE_DONE)
    bot_request.done = True
    logger.debug(f"Bot request {bot_request.request_time} done.")


@app.route('/v1/chat', methods=['POST'])
async def v1_chat():
    """同步请求，等待处理完毕返回结果"""
    data = await request.get_json()
    bot_request = construct_bot_request(data)
    await process_request(bot_request)
    # Return the result as JSON
    return bot_request.result.to_json()


@app.route('/v2/chat', methods=['POST'])
async def v2_chat():
    """异步请求，立即返回，通过/v2/chat/response获取内容"""
    data = await request.get_json()
    bot_request = construct_bot_request(data)
    asyncio.create_task(process_request(bot_request))
    request_dic[bot_request.request_time] = bot_request
    # Return the result time as request_id
    return bot_request.request_time


@app.route('/v2/chat/response', methods=['GET'])
async def v2_chat_response():
    """异步请求时，配合/v2/chat获取内容"""
    request_id = request.args.get("request_id")
    request_id = re.sub(r'^[%22%27"\'"]*|[%22%27"\'"]*$', '', request_id)     # 添加替换操作，以兼容头部和尾部带有引号和URL编码引号的request_id。
    bot_request: BotRequest = request_dic.get(request_id, None)
    if bot_request is None:
        return ResponseResult(message="没有更多了！", result_status=RESPONSE_FAILED).to_json()
    response = bot_request.result.to_json()
    if bot_request.done:
        request_dic.pop(request_id)
    else:
        bot_request.result.pop_all()
    logger.debug(f"Bot request {request_id} response -> \n{response[:100]}")
    return response


def clear_request_dict():
    logger.debug("Watch and clean request_dic.")
    while True:
        now = time.time()
        keys_to_delete = []
        for key, bot_request in request_dic.items():
            if now - int(key)/1000 > 600:
                logger.debug(f"Remove time out request -> {key}|{bot_request.session_id}|{bot_request.username}"
                             f"|{bot_request.message}")
                keys_to_delete.append(key)
        for key in keys_to_delete:
            request_dic.pop(key)
        time.sleep(60)


def construct_bot_request(data):
    session_id = data.get('session_id') or "friend-default_session"
    username = data.get('username') or "某人"
    message = data.get('message')
    logger.info(f"Get message from {session_id}[{username}]:\n{message}")
    with lock:
        bot_request = BotRequest(session_id, username, message, str(int(time.time() * 1000)))
    return bot_request


async def start_task():
    """|coro|
    以异步方式启动
    """
    threading.Thread(target=clear_request_dict).start()
    return await app.run_task(host=config.http.host, port=config.http.port, debug=config.http.debug)
