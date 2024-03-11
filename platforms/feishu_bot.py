import asyncio
import base64
import hashlib
import json
import threading
import time

import lark_oapi as lark
from Crypto.Cipher import AES
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.element import Plain
from lark_oapi.api.im.v1 import (CreateMessageResponse, CreateMessageRequest,
                                 CreateMessageRequestBody, CreateImageRequest,
                                 CreateImageRequestBody)
from loguru import logger
from quart import Quart, request, make_response

import constants
from constants import config
from universal import handle_message

Port = config.feishu.port
AppId = config.feishu.app_id
AppSecret = config.feishu.app_secret
Token = config.feishu.token
EncryptKey = config.feishu.encrypt_key
# 创建client
client = lark.Client.builder().app_id(AppId).app_secret(AppSecret).log_level(lark.LogLevel.DEBUG).build()
app = Quart(__name__)

lock = threading.Lock()

request_dic = {}

RESPONSE_SUCCESS = "SUCCESS"
RESPONSE_FAILED = "FAILED"
RESPONSE_DONE = "DONE"


class BotRequest:
    def __init__(self, session_id, user_id, receive_id_type, username, message, request_time):
        self.session_id: str = session_id
        self.user_id: str = user_id
        self.receive_id_type: str = receive_id_type
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
            'image': self.image
        })


class InvalidEventException(Exception):
    def __init__(self, error_info):
        self.error_info = error_info

    def __str__(self) -> str:
        return "Invalid event: {}".format(self.error_info)


class AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return self.decrypt(enc).decode('utf8')


class Obj(dict):
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
                setattr(self, a, [Obj(x) if isinstance(x, dict) else x for x in b])
            else:
                setattr(self, a, Obj(b) if isinstance(b, dict) else b)


def dict_2_obj(d: dict):
    return Obj(d)


def _send_text(receive_id_type, receive_id, msg):
    # 发送消息
    option = lark.RequestOption.builder().build()
    create_message_req = CreateMessageRequest.builder() \
        .receive_id_type(receive_id_type) \
        .request_body(CreateMessageRequestBody.builder()
                      .receive_id(receive_id)
                      .msg_type("text")
                      .content(lark.JSON.marshal({"text": msg}))
                      .build()) \
        .build()

    create_message_resp: CreateMessageResponse = client.im.v1.message.create(create_message_req, option)

    if not create_message_resp.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, "
            f"code: {create_message_resp.code}, "
            f"msg: {create_message_resp.msg}, "
            f"log_id: {create_message_resp.get_log_id()}")
    return create_message_resp


def _send_image(receive_id_type, receive_id, image):
    # 上传文件
    create_image_req = CreateImageRequest.builder() \
        .request_body(CreateImageRequestBody.builder()
                      .image_type("message")
                      .image(image)
                      .build()) \
        .build()

    create_image_resp = client.im.v1.image.create(create_image_req)

    if not create_image_resp.success():
        lark.logger.error(
            f"client.im.v1.image.create failed, "
            f"code: {create_image_resp.code}, "
            f"msg: {create_image_resp.msg}, "
            f"log_id: {create_image_resp.get_log_id()}")
        return create_image_resp

    # 发送消息
    option = lark.RequestOption.builder().headers({"X-Tt-Logid": create_image_resp.get_log_id()}).build()
    create_message_req = CreateMessageRequest.builder() \
        .receive_id_type(receive_id_type) \
        .request_body(CreateMessageRequestBody.builder()
                      .receive_id(receive_id)
                      .msg_type("text")
                      .content(lark.JSON.marshal(create_image_resp.data))
                      .build()) \
        .build()

    create_message_resp: CreateMessageResponse = client.im.v1.message.create(create_message_req, option)

    if not create_message_resp.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, "
            f"code: {create_message_resp.code}, "
            f"msg: {create_message_resp.msg}, "
            f"log_id: {create_message_resp.get_log_id()}")
    return create_message_resp


def validate(my_request, encrypt_key):
    timestamp = my_request.headers.get("X-Lark-Request-Timestamp")
    nonce = my_request.headers.get("X-Lark-Request-Nonce")
    signature = my_request.headers.get("X-Lark-Signature")
    body = my_request.data
    bytes_b1 = (timestamp + nonce + encrypt_key).encode("utf-8")
    bytes_b = bytes_b1 + body
    h = hashlib.sha256(bytes_b)
    if signature != h.hexdigest():
        raise InvalidEventException("invalid signature in event")


def _decrypt_json(encrypt_json):
    logger.info(f"encrypt.get('encrypt')={encrypt_json.get('encrypt')}")
    cipher = AESCipher(EncryptKey)
    return json.loads(cipher.decrypt_string(encrypt_json.get('encrypt')))


@app.route("/event", methods=["POST"])
async def event():
    encrypt_json = await request.get_json()
    decrypt_string = _decrypt_json(encrypt_json)
    decrypt_json = dict_2_obj(decrypt_string)
    try:
        header = decrypt_json.header
        if header.token != Token:
            raise InvalidEventException("invalid token")

        if header.event_type == "im.message.receive_v1":
            event_json = decrypt_json.event
            event_id = header.event_id
            bot_request = construct_bot_request(event_json)
            request_dic[event_id] = bot_request
            asyncio.create_task(process_request(bot_request))
            request_dic[bot_request.request_time] = bot_request

            response = await make_response("ok")
            response.status_code = 200
            return response

        response = await make_response("ok")
        response.status_code = 200
        return response
    except AttributeError:
        if decrypt_json.type == "url_verification":
            response = await make_response(decrypt_string)
            response.status_code = 200
            return response
        else:
            response = await make_response()
            response.status_code = 404
            return response


async def reply(bot_request: BotRequest):
    UserId = bot_request.user_id
    receive_id_type = bot_request.receive_id_type
    response = bot_request.result.to_json()
    if bot_request.done:
        request_dic.pop(bot_request.request_time)
    else:
        bot_request.result.pop_all()
    logger.debug(
        f"Bot request {bot_request.request_time} response -> \n{response[:100]}")
    if bot_request.result.message:
        for msg in bot_request.result.message:
            result = _send_text(receive_id_type, UserId, msg)
            logger.debug(f"Send message result -> {result}")
    if bot_request.result.image:
        for image in bot_request.result.image:
            result = _send_image(receive_id_type, UserId, image)
            logger.debug(f"Send image result -> {result}")


def clear_request_dict():
    logger.debug("Watch and clean request_dic.")
    while True:
        now = time.time()
        keys_to_delete = []
        for key, bot_request in request_dic.items():
            if now - int(key) / 1000 > 600:
                logger.debug(f"Remove time out request -> {key}|{bot_request.session_id}|{bot_request.username}"
                             f"|{bot_request.message}")
                keys_to_delete.append(key)
        for key in keys_to_delete:
            request_dic.pop(key)
        time.sleep(60)


def construct_bot_request(data):
    session_id = f"feishu-{str(data.message.chat_id)}" or "feishu-default_session"
    chat_type = data.message.chat_type
    if chat_type == "group":
        user_id = data.message.chat_id
        receive_id_type = "chat_id"
    elif chat_type == "p2p":
        user_id = data.sender.sender_id.open_id
        receive_id_type = "open_id"
    username = "某人"
    message = data.message.content
    logger.info(f"Get message from {session_id}[{user_id}]:\n{message}")
    with lock:
        bot_request = BotRequest(session_id, user_id, receive_id_type, username,
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
    return await app.run_task(host="0.0.0.0", port=Port, debug=config.feishu.debug)
