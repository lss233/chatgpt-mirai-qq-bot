import asyncio
import threading
import time
from queue import Queue

from flask import Flask, request, jsonify
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


async def process_request(bot_request: BotRequest):
    async def response(msg):
        logger.info(f"Got response msg -> {msg}")
        if isinstance(msg, str):
            bot_request.result = {
                "message": msg
            }
        else:
            logger.warning(f"Not support message -> {str(msg)}")
            bot_request.result = {
                "message": str(msg)
            }

    await handle_message(
        response,
        bot_request.session_id,
        bot_request.message,
        nickname=bot_request.username
    )


@app.route('/v1/chat/completions', methods=['POST'])
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


def main(multi_threads=False):
    if multi_threads:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    loop.run_until_complete(botManager.login())
    logger.info(f"Bot is ready. Logged in as http service!")
    run_simple(hostname=config.http.host, port=config.http.port, application=app, use_debugger=config.http.debug)
