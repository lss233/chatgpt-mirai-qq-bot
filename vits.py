import os
import requests
import datetime
from loguru import logger
from constants import config


def download_voice(base_url, text, lang, id, format, port):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"output_{timestamp}.{format}"

    save_dir = os.path.join('data', 'voice')

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, filename)

    url = f"{base_url}:{port}/voice?text={text}&lang={lang}&id={id}&format={format}"
    response = requests.get(url)

    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        logger.success(f"文件已保存到：{save_path}")
    else:
        logger.error(f"请求失败：{response.status_code}")
    return save_path


def response(text, format):
    host_url = config.vits.host_url
    lang = 'zh'
    id = config.vits.role_id
    port = config.vits.port
    return download_voice(host_url, text, lang, id, format, port)


def vits_api(message: str):
    if config.mirai:
        output_file = response(message, "ogg")
    else:
        output_file = response(message, "wav")

    return output_file
