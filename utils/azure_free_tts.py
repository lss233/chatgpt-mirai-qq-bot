import asyncio

import threading
from loguru import logger

# from constants import config

try:
    from graiax import silkcoder


    async def mp3_to_silk(input_data: bytes) -> bytes:
        return await silkcoder.async_encode(
            input_data,
            audio_format='mp3',
            ios_adaptive=True
        )
except ImportError as e:
    async def encode_to_silk(a=None):
        logger.warning("警告：Silk 转码模块无法加载，语音可能无法正常播放，请安装最新的 vc_redist 运行库。")
        return a

    # if config.text_to_speech.engine == 'azure':
    #     asyncio.run(encode_to_silk())

try:
    # import azure.cognitiveservices.speech as speechsdk
    import websocket
    import uuid
    import json
    import time
    import queue
    import secrets
    import re
    from random import randint


    def gen_cid():
        return secrets.token_hex(16)


    def gen_ip():
        return str(randint(10, 255)) + \
               '.' + str(randint(10, 255)) + \
               '.' + str(randint(10, 255)) + \
               '.' + str(randint(10, 255))


    message_dict = {
    }
    byte_dict = {
    }


    class Stat:
        def __init__(self, val):
            self.val = val

        def assertStat(self, s: bytes):
            idx = s.find(bytes(self.val, 'utf-8'))
            return idx > 0


    START = Stat('Path:turn.start')
    END = Stat('Path:turn.end')
    AUDIO = Stat('Path:audio')


    def on_open(ws):
        logger.info("AzureFreeTTS Connection established")


    def on_close(ws, a1, a2):
        logger.error(f"AzureFreeTTS Connection closed: {a1}, {a2}")
        global websocket_thread, stop_event
        if isinstance(websocket_thread, threading.Thread):
            if isinstance(stop_event, threading.Event):
                stop_event.set()
                websocket_thread = None
                stop_event = None
        for key in list(message_dict.keys()):
            message_dict[key].put([])
            del message_dict[key]
        for key in list(byte_dict.keys()):
            del byte_dict[key]


    def on_message(ws, data):
        _data = data if isinstance(data, bytes) else bytes(data, 'utf-8')
        id_tag = bytes('X-RequestId:', 'utf-8')
        index = _data.find(id_tag)
        # logger.info(f"AzureFreeTTS Received message: {data}")
        id_index = index + len(id_tag)
        id_str = _data[id_index:id_index + 32].decode('utf-8')

        if START.assertStat(_data):
            byte_dict[id_str] = []

        elif AUDIO.assertStat(_data):
            audio_tag_bytes = bytes('Path:audio\r\n', 'utf-8')
            _bytes = byte_dict[id_str]
            audio_index = data.index(audio_tag_bytes)
            _bytes.extend(data[audio_index + len(audio_tag_bytes):])

        elif END.assertStat(_data):
            if id_str not in byte_dict:
                return
            _bytes = byte_dict[id_str]
            del byte_dict[id_str]
            if id_str not in message_dict:
                return
            _queue = message_dict[id_str]
            if _queue and isinstance(_queue, queue.Queue):
                _queue.put(_bytes)

        # else:
        #     logger.warning(f"unknown data: {data}")


    def on_ping(ws, data):
        logger.info(f"ping: {data}")
        ws.pong(data)


    def on_pong(ws, data):
        logger.info(f"pong: {data}")


    def sendHeartbeat():
        cid = gen_cid()
        logger.info(f"Send heartbeat data: {cid}")
        timestamp = int(time.time())
        ssml = 'X-Timestamp:' + str(timestamp) + '\r\nX-RequestId:' + cid + \
               '\r\nContent-Type:application/ssml+xml\r\nPath:ssml\r\n\r\n' + \
               '<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" ' \
               'xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US">' \
               '<voice name="en-US-JennyNeural">' \
               '<prosody rate="0%" pitch="0%">hi</prosody>' \
               '</voice>' \
               '</speak>'
        if isinstance(ws, websocket.WebSocketApp) and ws.keep_running:
            ws.send(ssml)


    ws = None
    websocket_thread = None
    stop_event = None
    ip = gen_ip()
    # websocket.enableTrace(True)
    ws_url = "wss://eastus.api.speech.microsoft.com/cognitiveservices/websocket/v1?TrafficType=AzureDemo&X-ConnectionId="
    # logger.info(f"X-Forwarded-For =======>>>>> {ip}")
    # X-Forwarded-For 伪造ip似乎不行呢，频繁调用有概率限流429
    header = {
        "X-real-ip": ip,
        "X-Forwarded-For": ip,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.41",
    }

    """
        text： 文本
        voice_name：语音类型
        style： 语气
        lexicon： 多音字典url
        rate： 语速
        pitch: 音调
    """


    def build_ssml(text: str, voice_name: str, style: str, lexicon: str = '', rate: int = -1, pitch: int = -1):
        rate_str = ('rate="' + str(rate) + '%"') if rate != -1 else ''
        pitch_str = ('pitch="' + str(pitch) + '%"') if pitch != -1 else ''
        lexicon_str = '<lexicon uri="' + lexicon + '"/>' if lexicon else ''
        return '<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" \
        xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US"> \
          <voice name="' + voice_name + '"> \
            ' + lexicon_str + ' \
            <mstts:express-as style="' + style + '"> \
              <prosody volume="+50.00%" ' + rate_str + ' ' + pitch_str + '>' + text + '</prosody> \
            </mstts:express-as> \
          </voice> \
        </speak>'


    def conn():
        global ws, websocket_thread, stop_event
        if ws is None or not ws.keep_running:
            stop_event = threading.Event()
            ws = websocket.WebSocketApp(ws_url + gen_cid(),
                                        header=header,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_close=on_close,
                                        on_ping=on_ping,
                                        on_pong=on_pong)

            websocket_thread = threading.Thread(target=lambda event: (
                ws.run_forever(),
                event.wait(),
                logger.info('Exit websocket_thread.')
            ), args={stop_event})
            websocket_thread.start()

            # 60s发送一次心跳维持连接
            def action(func=None):
                if func:
                    try:
                        func()
                    except RuntimeError:
                        print()
                if isinstance(websocket_thread, threading.Thread):
                    t = threading.Timer(60.0, action, args=[sendHeartbeat])
                    t.start()

            action()
            time.sleep(3)
        return ws


    async def azure_free_speech(text: str, voice_name: str = 'zh-CN-XiaoyiNeural', style: str = 'affectionate'):
        cid = gen_cid()
        ssml = build_ssml(text, voice_name, style)
        timestamp = int(time.time())
        speechConfig = {
            "context": {
                "synthesis": {
                    "audio": {
                        "metadataoptions": {
                            "sentenceBoundaryEnabled": "false",
                            "wordBoundaryEnabled": "false",
                        },
                        "outputFormat": "audio-48khz-96kbitrate-mono-mp3",
                    }
                }
            }
        }
        config_body = 'X-Timestamp:' + str(timestamp) \
                      + '\r\nContent-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n' \
                      + json.dumps(speechConfig)
        ssml_body = 'X-Timestamp:' + str(timestamp) + '\r\nX-RequestId:' + cid + \
                    '\r\nContent-Type:application/ssml+xml\r\nPath:ssml\r\n\r\n' + ssml
        result = None

        def action():
            _ws = conn()
            _ws.send(config_body)
            _ws.send(ssml_body)
            msg_queue = queue.Queue()
            message_dict[cid] = msg_queue
            # logger.info(f'send cid:{cid}')
            data = msg_queue.get()
            return data

        if cid in message_dict:
            del message_dict[cid]
        return retry(action)


    def retry(func, count=2):
        error = None
        result = None
        while count >= 0:
            try:
                result = func()
                if len(result) > 0:
                    break
                count -= 1
            except Exception as err:
                logger.warning("azure free api execute error! retry ...")
                count -= 1
                error = err
        if error:
            raise error
        return result

except FileNotFoundError as e:
    async def synthesize_speech(a=None, b=None, c=None):
        logger.error("错误：Azure TTS 服务无法加载，请安装最新的 vc_redist 运行库。")
        logger.error("参考链接：")
        logger.error("https://github.com/lss233/chatgpt-mirai-qq-bot/issues/447")
        return None

    # if config.text_to_speech.engine == 'azure':
    #     asyncio.run(synthesize_speech())
