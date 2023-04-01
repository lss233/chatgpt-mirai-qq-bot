import os
import requests
import datetime
import re
from loguru import logger
from constants import config
from requests.exceptions import RequestException

import requests


def voice_speakers_check(id: int):
    url = "http://127.0.0.1:23456/voice/speakers"

    res = requests.post(url=url)
    json_data = res.json()

    # 遍历JSON数组，检查ID是否存在
    id_found = False
    for item in json_data:
        if str(id) in item.values():
            id_found = True
            break

    # 如果ID不存在，抛出异常
    if not id_found:
        raise Exception("ID not found in JSON array")

    return id


def download_voice(base_url, text, lang, id, format, port):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"output_{timestamp}.{format}"

    save_dir = os.path.join('voicedata')

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, filename)

    url = f"{base_url}:{port}/voice?text={text}&lang={lang}&id={id}&format={format}"
    try:
        response = requests.get(url)
    except RequestException as e:
        logger.error(f"请求失败：{str(e)}")
        return None

    if response.status_code == 200:
        try:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            logger.success(f"文件已保存到：{save_path}")
        except IOError as e:
            logger.error(f"文件写入失败：{str(e)}")
            return None
    else:
        logger.error(f"请求失败：{response.status_code}")
        return None

    return save_path


def linguistic_process(text: str, lang: str):
    matched_text = ''
    if "mix" == lang:
        regex = r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\w]+'
        matches = re.findall(regex, text)
        for match in matches:
            if re.search('[\u4e00-\u9fff]+', match):
                matched_text += '[ZH]' + match + '[ZH]'
            elif re.search('[\u3040-\u309f\u30a0-\u30ff]+', match):
                matched_text += '[JA]' + match + '[JA]'
            elif re.search('\w+', match):
                matched_text += "[ZH]还有一些我不会说，抱歉[ZH]"
    elif "zh" == lang:
        regex = r'[\u4e00-\u9fff]+'
        matches = re.findall(regex, text)
        matched_text = ''.join(matches)
    elif "ja" == lang:
        regex = r'[\u3040-\u309f\u30a0-\u30ff]+'
        matches = re.findall(regex, text)
        matched_text = ''.join(matches)
    return matched_text


def response(text, format):
    host_url = config.vits.host_url
    lang = 'mix'
    id = voice_speakers_check(config.vits.role_id)
    port = config.vits.port
    text = linguistic_process(text)
    return download_voice(host_url, text, lang, id, format, port)


def vits_api(message: str):
    if config.mirai:
        output_file = response(message, "silk")
    else:
        output_file = response(message, "wav")

    return output_file
