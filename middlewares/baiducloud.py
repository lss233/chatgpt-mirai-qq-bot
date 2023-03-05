import json
from typing import Union, Callable
import aiohttp
from loguru import logger
from config import Config

from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group
from middlewares.middleware import Middleware
from graia.ariadne.message.element import Image

config = Config.load_config()


class MiddlewareBaiduCloud(Middleware):
    def __init__(self):
        ...

    async def handle_respond(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             rendered: str, respond: Callable, action: Callable):
        try:
            if config.baiducloud.check:
                async with aiohttp.ClientSession() as session:
                    async with session.post("https://aip.baidubce.com/oauth/2.0/token", params={
                        "grant_type": "client_credentials",
                        "client_id": config.baiducloud.baidu_api_key,
                        "client_secret": config.baiducloud.baidu_secret_key,
                    }) as response:
                        response.raise_for_status()
                        result = await response.json()
                        access_token = result.get("access_token")
                        baidu_url = f"https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined" \
                                    f"?access_token={access_token}"
                        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

                    # 不处理图片信息
                    if isinstance(rendered, Image):
                        return await action(session_id, source, target, prompt, rendered, respond)

                    async with session.post(baidu_url, headers=headers, data={'text': rendered}) as response:
                        response.raise_for_status()
                        response_dict = await response.json()

                # 处理百度云审核结果
                    conclusion = response_dict["conclusion"]
                    if conclusion in ("合规"):
                        logger.success(f"百度云判定结果：{conclusion}")
                        return await action(session_id, source, target, prompt, rendered, respond)
                    else:
                        msg = response_dict['data'][0]['msg']
                        logger.error(f"百度云判定结果：{conclusion}")
                        conclusion = f"{config.baiducloud.illgalmessage}\n原因：{msg}"
                        return await action(session_id, source, target, prompt, conclusion, respond)
            # 未审核消息路径
            else:
                return await action(session_id, source, target, prompt, rendered, respond)
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error occurred: {e}")
            conclusion = f"百度云判定出错\n以下是原消息：{rendered}"
            return await action(session_id, source, target, prompt, conclusion, respond)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error occurred: {e}")
        except StopIteration as e:
            logger.error(f"StopIteration exception occurred: {e}")
