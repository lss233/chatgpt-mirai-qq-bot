import argparse
import base64
import datetime
# from common.log import logger
import os

import requests
from PIL import Image, PngImagePlugin
import time
import random
import io
import re
from loguru import logger


def clean_file_name(filename: str):
    invalid_chars = '[\\\/:*?"<>|]'
    replace_char = ','
    return re.sub(invalid_chars, replace_char, filename)[:140]


def getTimeStamp():
    t = time.localtime(time.time())
    return f'{str(t.tm_year)}_{str(t.tm_mon)}_{str(t.tm_mday)}_{str(t.tm_hour)}_{str(t.tm_min)}_{str(t.tm_sec)}{random.randint(10, 99)}'


def get_pic_size_W(PROMPT):
    sentence = PROMPT

    pat = re.compile(r"(w)[:]([1-9]\d{3,}|[1-9]\d{1,2}|[1-9])")

    num_list = []
    for match in pat.finditer(sentence):
        num = match.group(2)
        if int(num) >= 512 and int(num) <= 1200:
            num_list.append(int(num))
        else:
            num_list.append(768)
        break  # 只匹配第一个符合条件的 W: 后面的数字
    if not num_list:
        num_list.append(768)
    return num_list


def get_pic_size_H(PROMPT):
    sentence = PROMPT
    pat = re.compile(r"(h)[:]([1-9]\d{3,}|[1-9]\d{1,2}|[1-9])")
    num_list = []
    for match in pat.finditer(sentence):
        num = match.group(2)
        if int(num) >= 512 and int(num) <= 1200:
            num_list.append(int(num))
        else:
            num_list.append(768)
        break
    if not num_list:
        num_list.append(768)
    return num_list


def translate_CN_EN(text: str):
    url = "http://127.0.0.1:8084"
    prompt_in = text
    payload = {'prompt': prompt_in}
    headers = {
        'Content-Type': 'application/json'
    }
    resp = requests.post(url='http://127.0.0.1:8084/api/translation', json=payload, headers=headers)
    return resp.json()["data"] if resp.status_code == 200 else prompt_in


def b64_img(image: Image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return 'data:image/png;base64,' + str(
        base64.b64encode(buffered.getvalue()), 'utf-8'
    )


def text_to_img(PROMPT_WX, model_num='dalcefoPainting_3rd.safetensors[7107c05c1c]'):
    t_stamp = getTimeStamp()
    url = "http://127.0.0.1:7861"
    w_size = get_pic_size_W(PROMPT_WX)[0]
    h_size = get_pic_size_H(PROMPT_WX)[0]
    PROMPT_WX_00 = PROMPT_WX.replace(f"w:{w_size}", "").replace(f"h:{h_size}", "")
    download_img_path = (
        'D:/TG图片生成/' + datetime.datetime.now().strftime("%Y-%m-%d") + '/'
    )
    if not os.path.exists(download_img_path):
        os.makedirs(download_img_path)
    # PROMPT_WX_01 = translate_CN_EN(PROMPT_WX_01)

    tran_pattern = re.compile('[\u4e00-\u9fa5]+')
    if tran_text := tran_pattern.findall(PROMPT_WX_00):
        for word in tran_text:
            english_word = translate_CN_EN(word)
            PROMPT_WX_01 = PROMPT_WX_00.replace(word, english_word)  # 将中文字符用英文字符进行替换
    else:
        PROMPT_WX_01 = PROMPT_WX_00
    prompt_in = f'masterpiece, best quality, illustration, extremely detailed 8K wallpaper, {str(PROMPT_WX_01)}'
    payload = {
        'enable_hr': 'false',
        'denoising_strength': 0.45,
        'prompt': prompt_in,
        'steps': 15,
        'seed': -1,
        'batch_size': 1,
        'n_iter': 1,
        'cfg_scale': 7.5,
        'width': w_size,
        'height': h_size,
        'restore_faces': 'false',
        'tiling': 'false',
        'negative_prompt': 'NG_DeepNegative_V1_75T, badhandv4, EasyNegative, bad hands, missing fingers, cropped legs, worst quality, low quality, normal quality, jpeg artifacts, blurry,missing arms, long neck, Humpbacked,multiple breasts, mutated hands and fingers, long body, mutation, poorly drawn , bad anatomy,bad shadow,unnatural body, fused breasts, bad breasts, more than one person,wings on halo,small wings, 2girls, lowres, bad anatomy, text, error, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, out of frame, lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers,',
        'eta': 0,
        'sampler_index': 'DPM++ SDE Karras',
        "filter_nsfw": 'false'

    }

    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
    if response.status_code == 200:
        r = response.json()
    else:
        logger.debug("图片生成失败！")

    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

        png_payload = {"image": f"data:image/png;base64,{i}"}
        response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
        if response.status_code == 200:
            pnginfo = PngImagePlugin.PngInfo()
        else:
            logger.debug("图片生成失败！")
        pnginfo.add_text("parameters", response2.json().get("info"))
        path_save_img = f'{download_img_path}TG_{t_stamp}.png'
        image.save(path_save_img, pnginfo=pnginfo)
    return path_save_img


def img_to_img(src_img, PROMPT_WX, model_num='dalcefoPainting_3rd.safetensors[7107c05c1c]'):
    t_stamp = getTimeStamp()
    url = "http://127.0.0.1:7861"
    w_size = get_pic_size_W(PROMPT_WX)[0]
    h_size = get_pic_size_H(PROMPT_WX)[0]
    PROMPT_WX_00 = PROMPT_WX.replace(f"w:{w_size}", "").replace(f"h:{h_size}", "")
    download_img_path = 'D:/TG图生图/'
    # PROMPT_WX_01 = translate_CN_EN(PROMPT_WX_01)

    tran_pattern = re.compile('[\u4e00-\u9fa5]+')
    tran_text = tran_pattern.findall(PROMPT_WX_00)
    if tran_text:
        for word in tran_text:
            english_word = translate_CN_EN(word)
            PROMPT_WX_01 = PROMPT_WX_00.replace(word, english_word)  # 将中文字符用英文字符进行替换
    else:
        PROMPT_WX_01 = PROMPT_WX_00

    for word in tran_text:
        english_word = translate_CN_EN(word)
        PROMPT_WX_01 = PROMPT_WX_00.replace(word, english_word)  # 将中文字符用英文字符进行替换
    prompt_in = f'masterpiece, best quality, illustration, extremely detailed 8K wallpaper, {str(PROMPT_WX_01)}'
    payload = {
        'init_images': [b64_img(x) for x in src_img],
        'enable_hr': 'false',
        'denoising_strength': 0.45,
        'prompt': prompt_in,
        'steps': 20,
        'seed': -1,
        'batch_size': 1,
        'n_iter': 1,
        'cfg_scale': 7.5,
        'width': w_size,
        'height': h_size,
        'restore_faces': 'false',
        'tiling': 'false',
        'negative_prompt': 'NG_DeepNegative_V1_75T, EasyNegative, bad hands, missing fingers, cropped legs, worst quality, low quality, normal quality, jpeg artifacts, blurry,missing arms, long neck, Humpbacked,multiple breasts, mutated hands and fingers, long body, mutation, poorly drawn , bad anatomy,bad shadow,unnatural body, fused breasts, bad breasts, more than one person,wings on halo,small wings, 2girls, lowres, bad anatomy, text, error, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, out of frame, lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers,',
        'eta': 0,
        'sampler_index': 'DDIM',
        "filter_nsfw": 'false'

    }

    response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload)
    if response.status_code == 200:
        r = response.json()
    else:
        logger.debug("图片生成失败！")

    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

        png_payload = {"image": f"data:image/png;base64,{i}"}
        response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
        if response.status_code == 200:
            pnginfo = PngImagePlugin.PngInfo()
        else:
            logger.debug("图片生成失败！")
        pnginfo.add_text("parameters", response2.json().get("info"))
        path_save_img = f'{download_img_path}TG_{t_stamp}.png'
        image.save(path_save_img, pnginfo=pnginfo)
    return path_save_img


# model_01 = 'anything-v4.5.safetensors[1d1e459f9f]',
# model_02 = 'chilloutmix_.safetensors[a757fe8b3d]',
# model_03 = 'dalcefoPainting_3rd.safetensors[7107c05c1c]'
# model_04 = 'dalcefoPainting_dalcefoV3Painting.safetensors[dce6b18d01]'
# DPM++ SDE Karras
# Euler a
if __name__ == '__main__':
    ff = '@AI助理克罗索 画sese:1girl,best quality, ultra high res, naked,pussy,big breast,(photorealistic:1.3), nsfw, POV ,(solo:1.1), (1girl:1.1), (hanfugirl:1.4),adolescent, (nsfw:1.4641), (topless:1.4641), (open clothes:1.1), (doggystyle:1.331), (happy sex:1.2), (no panties:1.4), (off shoulder:1.1), (looking at viewer:1.331), (large breasts:1.61), (nipple:1.4641), hanfugirl, black hair, blunt bangs, parted bangs, high ponytail, half updo, (crown braid:1.21), braided bun, earrings, (half naked hanfu:1.414), (parted lips:1.1), (eyelashes:1.1), (happy:1.21), (depth of field:1.1), lens flare, (chromatic aberration:1.1), (caustics:1.1), in summer, (water:1.331), (water splash:1.21), branch, (beautiful detailed sky:1.331), (flower on liquid:1.331), (scattered luminous petals:1.331), ulzzang-6500,(keta-31500:0.75)'
    af = '@AI助理克罗索 画sese:一个女孩正在河边玩耍'
    send_SD_img(af)
