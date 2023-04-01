import os
import requests
import datetime
import re
from loguru import logger
from constants import config
from requests.exceptions import RequestException

import requests


def check_id_exists(json_array, given_id):
    for item in json_array:
        if str(given_id) in item:
            return True
    return False


def voice_speakers_check(host_url, port, id: int):
    url = f"{host_url}:{port}/voice/speakers"
    res = requests.post(url=url)
    json_array = res.json()

    result = check_id_exists(json_array, id)

    # 如果ID不存在，抛出异常
    if not result:
        raise Exception("不存在该语音音色，请检查配置文件")

    return id


def download_voice(base_url, text, lang, id, format, port, speed):
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
    lang = config.vits.lang
    port = config.vits.port
    id = voice_speakers_check(host_url, port, config.vits.role_id)
    text = linguistic_process(text, lang)
    speed = config.vits.speed
    return download_voice(host_url, text, lang, id, format, port, speed)


def vits_api(message: str):
    if config.mirai:
        output_file = response(message, "silk")
    else:
        output_file = response(message, "wav")

    return output_file
