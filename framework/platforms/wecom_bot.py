# -*- coding: utf-8 -*-
import functools
from io import BytesIO

import asyncio
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger
from quart import Quart, request, abort, make_response
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.work import parse_message, create_reply
from wechatpy.work.client import WeChatClient
from wechatpy.work.crypto import WeChatCrypto
from wechatpy.work.exceptions import InvalidCorpIdException

from constants import config
from framework.messages import ImageElement
from framework.request import Request, Response
from framework.tts.tts import TTSResponse, VoiceFormat
from framework.universal import handle_message

CorpId = config.wecom.corp_id
AgentId = config.wecom.agent_id
Secret = config.wecom.secret
TOKEN = config.wecom.token
EncodingAESKey = config.wecom.encoding_aes_key
crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
client = WeChatClient(CorpId, Secret)


async def _response_func(UserId: str, chain: MessageChain, text: str, voice: TTSResponse, image: ImageElement):
    if text:
        client.message.send_text(AgentId, UserId, text)
    if image:
        image_id = client.media.upload(
            "image", BytesIO(await image.get_bytes()))["media_id"]
        client.message.send_image(AgentId, UserId, image_id)
    if voice:
        voice_id = client.media.upload(
            "voice", await voice.transcode(VoiceFormat.Amr))["media_id"]
        client.message.send_voice(AgentId, UserId, voice_id)


def route(app: Quart):
    """注册 HTTP 路由"""
    @app.get("/wechat")
    async def echo_str():
        signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        try:
            return crypto.check_signature(
                signature, timestamp, nonce, request.args.get("echostr", ""))
        except InvalidSignatureException:
            logger.error("签名检查失败，请检查配置是否正确。")
            return abort(403)

    @app.post("/wechat")
    async def wechat():
        signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        try:
            msg = crypto.decrypt_message(await request.data, signature, timestamp, nonce)
        except (InvalidSignatureException, InvalidCorpIdException):
            logger.error("消息解密失败，请检查配置是否正确。")
            return abort(403)
        msg = parse_message(msg)
        logger.debug(msg)
        if msg.type == "text":
            _reply = create_reply(msg.content, msg).render()

            _request = Request()
            _request.session_id = f"wecom-{str(msg.source)}"
            _request.user_id = msg.source
            _request.nickname = client.user.get(msg.source) or "某人"
            _request.message = MessageChain([Plain(msg.content)])
            logger.info(f"Get message from {_request.session_id}:\n{_request.message}")

            _response = Response(functools.partial(_response_func, UserId=msg.source))

            asyncio.create_task(handle_message(_request, _response))

            response = await make_response("ok")
            response.status_code = 200
            return response
        else:
            _reply = create_reply("Can not handle this for now", msg).render()
        return crypto.encrypt_message(_reply, nonce, timestamp)
