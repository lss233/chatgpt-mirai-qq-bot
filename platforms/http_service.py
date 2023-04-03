import asyncio

from flask import Flask, request, jsonify
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from loguru import logger
from werkzeug.serving import run_simple

from constants import botManager, config
from universal import handle_message

app = Flask(__name__)


class BotRequest:
    def __init__(self, session_id, username, message):
        self.session_id = session_id
        self.username = username
        self.message = message
        self.result = None

    def append_result_message(self, message):
        if not self.result:
            self.result = {
                "message": message
            }
        elif not self.result["message"]:
            self.result["message"] = message
        else:
            self.result["message"] = f'{self.result["message"]}\n{message}'


async def process_request(bot_request: BotRequest):
    async def response(msg):
        logger.info(f"Got response msg -> {msg}")
        _resp = msg
        if not isinstance(msg, MessageChain):
            _resp = MessageChain(msg)
        for ele in _resp:
            if isinstance(ele, str):
                bot_request.append_result_message(ele)
            elif isinstance(ele, Image):
                bot_request.append_result_message(f'<img src="data:image/png;base64,{ele.base64}"/>')
            else:
                logger.warning(f"Unsupported message -> {str(ele)}")
                bot_request.append_result_message(str(ele))

    await handle_message(
        response,
        bot_request.session_id,
        bot_request.message,
        nickname=bot_request.username
    )


@app.route('/v1/chat', methods=['POST'])
async def chat_completions():
    session_id = request.json.get('session_id') or "friend-default_session"
    username = request.json.get('username') or "某人"
    message = request.json.get('message')
    logger.info(f"Get message from {session_id}[{username}]:\n{message}")
    if message is None or str(message).strip() == '':
        return '{"message": "message 不能为空！"}'
    # Create a new BotRequest object and add it to the queue
    bot_request = BotRequest(session_id, username, message)
    await process_request(bot_request)
    # Return the result as JSON
    return jsonify(bot_request.result)


def main(event_loop=asyncio.get_event_loop()):
    asyncio.set_event_loop(event_loop)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(botManager.login())
    logger.info(f"Bot is ready. Logged in as http service!")
    run_simple(hostname=config.http.host, port=config.http.port, application=app, use_debugger=config.http.debug)
