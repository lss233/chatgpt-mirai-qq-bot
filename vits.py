import mirai
import os
import platform
import re
import requests
import datetime
from constants import config


def download_voice(base_url, text, lang, id, format, port):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"output_{timestamp}.{format}"

    # 构建跨平台的路径

    save_dir = os.path.join('data', 'voice')

    # 如果目录不存在就创建它
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, filename)

    url = f"{base_url}:{port}/voice?text={text}&lang={lang}&id={id}&format={format}"
    response = requests.get(url)

    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"文件已保存到：{save_path}")
    else:
        print(f"请求失败：{response.status_code}")
    return save_path


def response(text, format):
    base_url = 'http://127.0.0.1'
    lang = 'zh'
    id = 3
    port = 23456
    return download_voice(base_url, text, lang, id, format, port)


def vits_api(message: str):
    if config.mirai:
        output_file = response(message, "ogg")
    else:
        output_file = response(message, "wav")

    return output_file
