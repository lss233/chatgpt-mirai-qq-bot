import json
from typing import Callable

import aiohttp
from graia.ariadne.message.element import Image
from loguru import logger

from config import Config
from middlewares.middleware import Middleware

config = Config.load_config()


async def get_access_token():
    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": config.baiducloud.baidu_api_key,
                    "client_secret": config.baiducloud.baidu_secret_key,
                }
        ) as response:
            response.raise_for_status()
            result = await response.json()
            access_token = result.get("access_token")

            # 保存access_token到文件
            data = {"access_token": access_token}
            with open("data/baidu_access_token.json", "w") as f:
                json.dump(data, f)

            return access_token


async def read_access_token():
    try:
        with open("data/baidu_access_token.json", "r") as f:
            data = json.load(f)
            access_token = data["access_token"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        access_token = None

    return access_token


class MiddlewareBaiduCloud(Middleware):
    def __init__(self):
        ...

    async def handle_respond(self, session_id: str, prompt: str, rendered: str, respond: Callable, action: Callable):
        try:
            if config.baiducloud.check:
                access_token = await read_access_token()
                if not access_token:
                    logger.debug(f"正在获取access_token，请稍等")
                    access_token = await get_access_token()

                baidu_url = f"https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined" \
                            f"?access_token={access_token}"
                headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

                # 不处理图片信息
                if isinstance(rendered, Image):
                    return await action(session_id, prompt, rendered, respond)

                async with aiohttp.ClientSession() as session:
                    async with session.post(baidu_url, headers=headers, data={'text': str(rendered)}) as response:
                        response.raise_for_status()
                        response_dict = await response.json()

                    # 处理百度云审核结果
                    conclusion = response_dict["conclusion"]
                    if conclusion in "合规":
                        logger.success(f"百度云判定结果：{conclusion}")
                        return await action(session_id, prompt, rendered, respond)
                    else:
                        msg = response_dict['data'][0]['msg']
                        logger.error(f"百度云判定结果：{conclusion}")
                        conclusion = f"{config.baiducloud.illgalmessage}\n原因：{msg}"
                        return await action(session_id, prompt, conclusion, respond)
            # 未审核消息路径
            else:
                return await action(session_id, prompt, rendered, respond)
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error occurred: {e}")
            conclusion = f"百度云判定出错\n以下是原消息：{rendered}"
            return await action(session_id, prompt, conclusion, respond)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error occurred: {e}")
        except StopIteration as e:
            logger.error(f"StopIteration exception occurred: {e}")
