import base64
import json
import typing
import random
import os.path
from functools import wraps

import asyncio

import contextlib
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from quart import Quart, request, make_response, jsonify, send_from_directory, safe_join
from werkzeug.security import generate_password_hash, check_password_hash

import constants
from framework.accounts import account_manager
from framework.messages import ImageElement
from framework.request import Request, Response
from framework.tts.tts import TTSResponse, VoiceFormat
from framework.universal import handle_message
import hashlib
from loguru import logger
from datetime import datetime, timedelta
import jwt
import time

from datetime import timezone

login_attempts = {}

if not constants.config.http.password:
    password = "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10))
    logger.warning("=====================================")
    logger.warning(" ")
    logger.warning(" 警告：未设置 HTTP 控制台密码")
    logger.warning(f" 已为您生成密码：{password}")
    logger.warning(" 请妥善保存")
    logger.warning(" ")
    logger.warning("=====================================")
    constants.config.http.password = generate_password_hash(password, method="sha512", salt_length=6)
    constants.Config.save_config(constants.config)

jwt_secret_key = hashlib.sha256(constants.config.http.password.encode('utf-8')).digest()

webui_static = safe_join(os.path.dirname(os.path.pardir), 'assets/webui')


def generate_token():
    """生成 JWT 令牌"""
    # 令牌有效期为 3 天
    expiration_time = datetime.now(timezone.utc) + timedelta(days=3)
    # 令牌的 payload 包含过期时间和密码哈希
    payload = {"exp": expiration_time}
    return jwt.encode(payload, jwt_secret_key, algorithm="HS256")


def authenticate(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 检查 Authorization 头
        token = request.headers.get("Authorization", '').removeprefix("Bearer ")
        if not token:
            return jsonify({"error": "认证失败"}), 401

        # 验证 JWT 令牌
        try:
            jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "令牌已过期"}), 401
        except Exception:
            return jsonify({"error": "无效的令牌"}), 401

        # 如果认证成功，则调用原始函数
        return await func(*args, **kwargs)

    return wrapper


def route(app: Quart):
    @app.post("/backend-api/v1/login")
    async def login():
        # 获取请求中的密码
        data = await request.get_json()
        if not data:
            return jsonify({"error": "密码不正确"}), 401

        # 防止暴力破解，限制登录尝试次数
        ip = request.remote_addr
        now = time.monotonic()
        if ip in login_attempts:
            failed_attempts, last_attempt_time = login_attempts[ip]
            if failed_attempts >= 6:
                wait_time = 600  # set wait time to 10 minutes
                seconds_since_last_attempt = int(now - last_attempt_time)
                remaining_wait_time = wait_time - seconds_since_last_attempt
                if remaining_wait_time > 0:
                    return jsonify({"error": f"登录失败次数过多，请在 {remaining_wait_time} 秒后重试"}), 429
            else:
                login_attempts[ip] = (failed_attempts + 1, now)
        else:
            login_attempts[ip] = (1, now)

        password_hash = constants.config.http.password
        # 检查密码
        if check_password_hash(password_hash, data.get("password", "")):
            # 生成 JWT 令牌
            token = generate_token()
            return jsonify({"token": token}), 200

        # 如果认证失败，则增加登录尝试次数并返回错误响应
        login_attempts[ip] = login_attempts.get(ip, (0, 0))
        login_attempts[ip] = (login_attempts[ip][0] + 1, now)
        return jsonify({"error": "密码不正确"}), 401

    @app.get('/backend-api/v1/config')
    @authenticate
    async def get_config():
        type = request.args.get("type", "schema")
        constants.config.json()
        if type == "value":
            if key := request.args.get("key", ''):
                return obj.json() if (obj := constants.config.__getattribute__(key)) else '{}'
            return constants.config.json()
        if key := request.args.get("key", ''):
            if not (type_ := typing.get_type_hints(constants.Config).get(key)):
                return ''
            if typing.get_origin(type_) is typing.Union:
                return typing.get_args(type_)[0].schema_json()
            else:
                return type_.schema_json()
        return constants.config.schema_json()

    @app.post('/backend-api/v1/config')
    @authenticate
    async def post_config():
        key = request.args.get("key", '')
        data = await request.get_json()
        parsed = json.loads(constants.config.json())
        parsed[key] = data
        parsed = constants.config.parse_obj(parsed)
        constants.config.save_config(parsed)
        constants.config = parsed

        return json.dump({
            "ok": True
        })

    @app.get("/backend-api/v1/accounts/list")
    @authenticate
    async def get_accounts():
        return {
            key: [item.dict() for item in value]
            for key, value in account_manager.loaded_accounts.items()
        }

    @app.get("/backend-api/v1/accounts/model")
    @authenticate
    async def get_account_model():
        key = request.args.get("key", "chatgpt-web")
        return account_manager.registered_models[key].schema_json()

    @app.post("/backend-api/v1/accounts/<key>/<index>")
    @authenticate
    async def update_account_model(key: str, index: str):
        data = await request.get_json()
        account = account_manager.registered_models[key].parse_obj(data)
        account_manager.loaded_accounts[key][int(index)] = account
        result = await account_manager.login_account(key, account)
        constants.config.accounts.__getattribute__(key)[int(index)] = account
        constants.config.save_config(constants.config)
        return json.dumps({
            "ok": result
        })

    @app.delete("/backend-api/v1/accounts/<key>/<index>")
    @authenticate
    async def delete_account_model(key: str, index: str):
        del account_manager.loaded_accounts[key][int(index)]
        del constants.config.accounts.__getattribute__(key)[int(index)]
        constants.config.save_config(constants.config)
        return json.dumps({
            "ok": True
        })

    @app.post("/backend-api/v1/accounts/<key>")
    @authenticate
    async def add_new_account(key: str):
        data = await request.get_json()
        account = account_manager.registered_models[key].parse_obj(data)
        account_manager.loaded_accounts[key].append(account)
        result = await account_manager.login_account(key, account)
        constants.config.accounts.__getattribute__(key).append(account)
        constants.config.save_config(constants.config)
        return json.dumps({
            "ok": result
        })

    @app.post('/v1/conversation')
    async def conversation():
        data = await request.get_json()

        _req = Request()
        _req.session_id = data.get("session_id")
        _req.user_id = data.get("user_id", "")
        _req.group_id = data.get("group_id", "")
        _req.nickname = data.get("nickname", "Bob")
        _req.is_manager = data.get("is_manager", False)
        prefered_format: VoiceFormat = data.get("prefered_format", VoiceFormat.Wav)
        message_chain = []
        for item in data.get("messages", []):
            type_ = item.get('type', 'text')
            if type_ == 'text':
                message_chain.append(Plain(item.get('value')))
            elif type_ == 'image':
                message_chain.append(ImageElement(base64=item.get('value')))
            elif type_ == 'voice':
                message_chain.append(
                    TTSResponse(format_=item.get('format'), data_bytes=base64.b64decode(item.get('value')),
                                text=item.get('text', '')))
        _req.message = MessageChain(message_chain)

        q = asyncio.Queue()

        async def _response_func(chain: MessageChain, text: str, voice: TTSResponse, image: ImageElement):
            response_chain = []
            if text:
                response_chain.append({
                    "type": "text",
                    "value": text
                })
            if voice:
                response_chain.append({
                    "type": "voice",
                    "value": await voice.get_base64(prefered_format),
                    "format": prefered_format.value
                })
            if image:
                response_chain.append({
                    "type": "image",
                    "value": image.base64
                })
            await q.put(response_chain)

        _res = Response(_response_func)

        task = asyncio.create_task(handle_message(_req, _res))

        async def send_events():

            while not task.done() and not task.cancelled():
                with contextlib.suppress(asyncio.TimeoutError):
                    message = json.dumps(await asyncio.wait_for(q.get(), 1), ensure_ascii=False)
                    message = f"data: {message}\r\n\r\n"
                    yield message.encode('utf-8')
                    q.task_done()

        response = await make_response(
            send_events(),
            {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            },
        )
        response.timeout = None
        return response

    @app.route('/')
    async def _home():
        return await send_from_directory(webui_static, 'index.html')

    @app.route('/<path:path>')
    async def _static(path):
        if os.path.isdir(safe_join(webui_static, path)):
            path = os.path.join(path, 'index.html')
        return await send_from_directory(webui_static, path)
