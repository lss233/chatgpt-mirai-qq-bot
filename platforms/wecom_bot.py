# -*- coding: utf-8 -*-
import json
import threading
import time
import asyncio
import base64
from io import BytesIO
from loguru import logger
from pydub import AudioSegment
from quart import Quart, request, abort, make_response

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Voice
from graia.ariadne.message.element import Plain

from wechatpy.work.crypto import WeChatCrypto
from wechatpy.work.client import WeChatClient
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.work.exceptions import InvalidCorpIdException
from wechatpy.work import parse_message, create_reply

import constants
from constants import config
from universal import handle_message

CorpId = config.wecom.corp_id
AgentId = config.wecom.agent_id
Secret = config.wecom.secret
TOKEN = config.wecom.token
EncodingAESKey = config.wecom.encoding_aes_key
crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
client = WeChatClient(CorpId, Secret)
app = Quart(__name__)

lock = threading.Lock()

request_dic = {}

RESPONSE_SUCCESS = "SUCCESS"
RESPONSE_FAILED = "FAILED"
RESPONSE_DONE = "DONE"


class BotRequest:
    def __init__(self, session_id, user_id, username, message, request_time):
        self.session_id: str = session_id
        self.user_id: str = user_id
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


@app.route("/wechat", methods=["GET", "POST"])
async def wechat():
    signature = request.args.get("msg_signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if request.method == "GET":
        echo_str = request.args.get("echostr", "")
        try:
            echo_str = crypto.check_signature(
                signature, timestamp, nonce, echo_str)
        except InvalidSignatureException:
            abort(403)
        return echo_str
    else:
        try:
            msg = crypto.decrypt_message(await request.data, signature, timestamp, nonce)
        except (InvalidSignatureException, InvalidCorpIdException):
            abort(403)
        msg = parse_message(msg)
        logger.debug(msg)
        if msg.type == "text":
            reply = create_reply(msg.content, msg).render()

            bot_request = construct_bot_request(msg)
            asyncio.create_task(process_request(bot_request))
            request_dic[bot_request.request_time] = bot_request

            response = await make_response("ok")
            response.status_code = 200
            return response
        else:
            reply = create_reply("Can not handle this for now", msg).render()
        return crypto.encrypt_message(reply, nonce, timestamp)


async def reply(bot_request: BotRequest):
    # client = WeChatClient(CorpId, Secret)
    UserId = bot_request.user_id
    response = bot_request.result.to_json()
    if bot_request.done:
        request_dic.pop(bot_request.request_time)
    else:
        bot_request.result.pop_all()
    logger.debug(
        f"Bot request {bot_request.request_time} response -> \n{response[:100]}")
    if bot_request.result.message:
        for msg in bot_request.result.message:
            result = client.message.send_text(AgentId, UserId, msg)
            logger.debug(f"Send message result -> {result}")
    if bot_request.result.voice:
        for voice in bot_request.result.voice:
            # convert mp3 to amr
            voice = convert_mp3_to_amr(voice)
            voice_id = client.media.upload(
                "voice", voice)["media_id"]
            result = client.message.send_voice(AgentId, UserId, voice_id)
            logger.debug(f"Send voice result -> {result}")
    if bot_request.result.image:
        for image in bot_request.result.image:
            image_id = client.media.upload(
                "image", BytesIO(base64.b64decode(image)))["media_id"]
            result = client.message.send_image(AgentId, UserId, image_id)
            logger.debug(f"Send image result -> {result}")


def convert_mp3_to_amr(mp3):
    mp3 = BytesIO(base64.b64decode(mp3))
    amr = BytesIO()
    AudioSegment.from_file(mp3,format="mp3").set_frame_rate(8000).set_channels(1).export(amr, format="amr", codec="libopencore_amrnb")
    return amr


def clear_request_dict():
    logger.debug("Watch and clean request_dic.")
    while True:
        now = time.time()
        keys_to_delete = []
        for key, bot_request in request_dic.items():
            if now - int(key)/1000 > 600:
                logger.debug(f"Remove time out request -> {key}|{bot_request.session_id}|{bot_request.user_id}"
                             f"|{bot_request.message}")
                keys_to_delete.append(key)
        for key in keys_to_delete:
            request_dic.pop(key)
        time.sleep(60)


def construct_bot_request(data):
    session_id = f"wecom-{str(data.source)}" or "wecom-default_session"
    user_id = data.source
    username = client.user.get(user_id) or "某人"
    message = data.content
    logger.info(f"Get message from {session_id}[{user_id}]:\n{message}")
    with lock:
        bot_request = BotRequest(session_id, user_id, username,
                                 message, str(int(time.time() * 1000)))
    return bot_request


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
                bot_request.append_result(
                    "image", ele.base64)
            elif isinstance(ele, Voice):
                # mp3
                bot_request.append_result(
                    "voice", ele.base64)
            else:
                logger.warning(
                    f"Unsupported message -> {type(ele)} -> {str(ele)}")
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
            request_from=constants.BotPlatform.WecomBot
        )
        bot_request.set_result_status(RESPONSE_DONE)
    bot_request.done = True
    logger.debug(f"Bot request {bot_request.request_time} done.")
    await reply(bot_request)


async def start_task():
    """|coro|
    以异步方式启动
    """
    threading.Thread(target=clear_request_dict).start()
    return await app.run_task(host=config.wecom.host, port=config.wecom.port, debug=config.wecom.debug)
