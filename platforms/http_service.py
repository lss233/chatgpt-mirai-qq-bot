from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.element import Plain
from loguru import logger
from quart import Quart, request, jsonify

from constants import config
from universal import handle_message

app = Quart(__name__)


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
        logger.info(f"Got response msg -> {type(msg)} -> {msg}")
        _resp = msg
        if not isinstance(msg, MessageChain):
            _resp = MessageChain(msg)
        for ele in _resp:
            if isinstance(ele, Plain) and str(ele):
                bot_request.append_result_message(str(ele))
            elif isinstance(ele, Image):
                bot_request.append_result_message(f'<img src="data:image/png;base64,{ele.base64}"/>')
            else:
                logger.warning(f"Unsupported message -> {type(ele)} -> {str(ele)}")
                bot_request.append_result_message(str(ele))

    await handle_message(
        response,
        bot_request.session_id,
        bot_request.message,
        nickname=bot_request.username
    )


@app.route('/v1/chat', methods=['POST'])
async def chat_completions():
    data = await request.get_json()
    session_id = data.get('session_id') or "friend-default_session"
    username = data.get('username') or "某人"
    message = data.get('message')
    logger.info(f"Get message from {session_id}[{username}]:\n{message}")
    if message is None or not str(message).strip():
        return '{"message": "message 不能为空！"}'
    # Create a new BotRequest object and add it to the queue
    bot_request = BotRequest(session_id, username, message)
    await process_request(bot_request)
    # Return the result as JSON
    return jsonify(bot_request.result)


async def start_task():
    """|coro|
    以异步方式启动
    """
    return await app.run_task(host=config.http.host, port=config.http.port, debug=config.http.debug)
