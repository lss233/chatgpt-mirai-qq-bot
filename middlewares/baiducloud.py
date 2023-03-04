from typing import Union, Callable
import requests
import json

from middlewares.middleware import Middleware
from graia.ariadne.message import Source
from graia.ariadne.model import Friend, Group
from config import Config
from loguru import logger

config = Config.load_config()


# 百度云审核调用函数
def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": config.baiducloud.baidu_api_key,
              "client_secret": config.baiducloud.baidu_secret_key}
    return str(requests.post(url, params=params).json().get("access_token"))


# 百度云审核URL
baidu_url = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined?access_token=" + get_access_token()


class MiddlewareBaiduCloud(Middleware):
    def __init__(self):
        ...

    async def handle_respond(self, session_id, source: Source, target: Union[Friend, Group], prompt: str,
                             rendered: str, respond: Callable, action: Callable):
        try:
            if config.baiducloud.check:
                # 百度云审核
                payload = "text=" + rendered
                logger.debug("向百度云发送:" + payload)
                headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

                if isinstance(payload, str):
                    payload = payload.encode('utf-8')

                response = requests.request("POST", baidu_url, headers=headers, data=payload)
                response_dict = json.loads(response.text)
                # 处理百度云审核结果
                if "error_code" in response_dict:
                    error_msg = response_dict.get("error_msg")
                    logger.error("百度云判定出错，错误信息：" + error_msg)
                    conclusion = f"百度云判定出错，错误信息：{error_msg}\n以下是原消息：{rendered}"
                else:
                    conclusion = response_dict["conclusion"]
                    if conclusion in ("合规"):
                        logger.success("百度云判定结果：" + conclusion)
                        return await action(session_id, source, target, prompt, rendered, respond)
                    else:
                        msg = response_dict['data'][0]['msg']
                        logger.error("百度云判定结果：" + conclusion)
                        conclusion = f"{config.baiducloud.illgalmessage}\n原因：{msg}"
                # 返回百度云审核结果
                return await action(session_id, source, target, prompt, conclusion, respond)
            # 未审核消息路径
            else:
                return await action(session_id, source, target, prompt, rendered, respond)
        except StopIteration:
            pass
