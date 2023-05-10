import base64
import json
import typing
import asyncio

import contextlib
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from quart import Quart, request, make_response

import constants
from framework.accounts import account_manager
from framework.messages import ImageElement
from framework.request import Request, Response
from framework.tts.tts import TTSResponse, VoiceFormat
from framework.universal import handle_message


def route(app: Quart):
    @app.get('/backend-api/v1/config')
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
    async def get_accounts():
        return {
            key: [item.dict() for item in value]
            for key, value in account_manager.loaded_accounts.items()
        }

    @app.get("/backend-api/v1/accounts/model")
    async def get_account_model():
        key = request.args.get("key", "chatgpt-web")
        return account_manager.registered_models[key].schema_json()

    @app.post("/backend-api/v1/accounts/<key>/<index>")
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
    async def delete_account_model(key: str, index: str):
        del account_manager.loaded_accounts[key][int(index)]
        del constants.config.accounts.__getattribute__(key)[int(index)]
        constants.config.save_config(constants.config)
        return json.dumps({
            "ok": True
        })

    @app.post("/backend-api/v1/accounts/<key>")
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
