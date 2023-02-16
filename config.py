from __future__ import annotations
from typing import List, Union, Literal
from pydantic import BaseModel, BaseConfig, Extra, Field
from charset_normalizer import from_bytes
from loguru import logger
import sys
import toml

class Mirai(BaseModel):
    qq: int
    """Bot 的 QQ 号"""
    api_key: str
    """mirai-api-http 的 verifyKey"""
    http_url: str = "http://localhost:8080"
    """mirai-api-http 的 http 适配器地址"""
    ws_url: str = "http://localhost:8080"
    """mirai-api-http 的 ws 适配器地址"""
class OpenAI(BaseModel):
    accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth, OpenAIAccessTokenAuth]]

class OpenAIAuthBase(BaseModel):
    mode: str = "browser"
    """OpenAI 的登录模式，可选的值：browserless - 无浏览器登录 browser - 浏览器登录"""
    proxy: Union[str, None] = None
    """可选的代理地址"""
    driver_exec_path: Union[str, None] = None
    """可选的 Chromedriver 路径"""
    browser_exec_path: Union[str, None] = None
    """可选的 Chrome 浏览器路径"""
    conversation: Union[str, None] = None
    """初始化对话所使用的UUID"""
    paid: bool = False
    """使用 ChatGPT Plus"""
    verbose: bool = False
    """启用详尽日志模式"""

    class Config(BaseConfig):
        extra = Extra.allow

class OpenAIEmailAuth(OpenAIAuthBase):
    email: str
    """OpenAI 注册邮箱"""
    password: str
    """OpenAI 密码"""
    isMicrosoftLogin: bool = False
    """是否通过 Microsoft 登录"""

class OpenAISessionTokenAuth(OpenAIAuthBase):
    session_token: str
    """OpenAI 的 session_token"""

class OpenAIAccessTokenAuth(OpenAIAuthBase):
    access_token: str
    """OpenAI 的 access_token"""

class OpenAIAPIKey(OpenAIAuthBase):
    api_key: str
    """OpenAI 的 api_key"""

class TextToImage(BaseModel):
    font_size: int = 30
    """字号"""
    width: int = 700
    """生成图片宽度"""
    font_path: str = "fonts/sarasa-mono-sc-regular.ttf"
    """字体路径"""
    offset_x: int = 50
    """横坐标"""
    offset_y: int = 50
    """纵坐标"""


class Trigger(BaseModel):
    prefix: List[str] = [""]
    """触发响应的前缀，默认不需要"""
    require_mention: Literal["at", "mention", "none"] = "at"
    """群内 [需要 @ 机器人 / 需要 @ 或以机器人名称开头 / 不需要 @] 才响应（请注意需要先 @ 机器人后接前缀）"""
    reset_command: List[str] = ["重置会话"]
    """重置会话的命令"""
    rollback_command: List[str] = ["回滚会话"]
    """回滚会话的命令"""


class Response(BaseModel):
    placeholder: str = (
        "您好！我是 Assistant，一个由 OpenAI 训练的大型语言模型。我不是真正的人，而是一个计算机程序，可以通过文本聊天来帮助您解决问题。如果您有任何问题，请随时告诉我，我将尽力回答。\n"
        "如果您需要重置我们的会话，请回复`重置会话`。"
    )
    """对空消息回复的占位符"""

    reset = "会话已重置。"
    """重置会话时发送的消息"""

    rollback_success = "已回滚至上一条对话，你刚刚发的我就忘记啦！"
    """成功回滚时发送的消息"""

    rollback_fail = "回滚失败，没有更早的记录了！"
    """回滚失败时发送的消息"""

    error_format: str = (
        "出现故障！如果这个问题持续出现，请和我说“重置会话” 来开启一段新的会话，或者发送 “回滚对话” 来回溯到上一条对话，你上一条说的我就当作没看见。"
        "\n{exc}"
    )
    """发生错误时发送的消息，请注意可以插入 {exc} 作为异常占位符"""

    quote: bool = True
    """是否回复触发的那条消息"""
    
    timeout: float = 30.0
    """发送提醒前允许的响应时间"""

    timeout_format: str = "我还在思考中，请再等一下~"
    """响应时间过长时要发送的提醒"""

    request_too_fast: str = "当前正在处理的请求太多了，请稍等一会再发吧！"
    """服务器提示 429 错误时的回复 """

    max_queue_size: int = 10
    """等待处理的消息的最大数量，如果要关闭此功能，设置为 0"""

    queue_full: str = "抱歉！我现在要回复的人有点多，暂时没有办法接收新的消息了，请过会儿再给我发吧！"
    """队列满时的提示"""

    queued_notice_size: int = 3
    """新消息加入队列会发送通知的长度最小值"""

    queued_notice: str = "消息已收到！当前我还有{queue_size}条消息要回复，请您稍等。"
    """新消息进入队列时，发送的通知。 queue_size 是当前排队的消息数"""

class System(BaseModel):
    accept_group_invite: bool = False
    """自动接收邀请入群请求"""

    accept_friend_request: bool = False
    """自动接收好友请求"""

class Preset(BaseModel):
    command: str = r"加载预设 (\w+)"
    keywords: dict[str, str] = dict()
    loaded_successful: str = "预设加载成功！"

class Config(BaseModel):
    mirai: Mirai
    openai: Union[OpenAI, OpenAIEmailAuth, OpenAISessionTokenAuth, OpenAIAccessTokenAuth]
    text_to_image: TextToImage = TextToImage()
    trigger: Trigger = Trigger()
    response: Response = Response()
    system: System = System()
    presets: Preset = Preset()

    def load_preset(self, keyword):
        try:
            with open(self.presets.keywords[keyword], "rb") as f:
                guessed_str = from_bytes(f.read()).best()
                if not guessed_str:
                    raise ValueError("无法识别预设的 JSON 格式，请检查编码！")
                
                return str(guessed_str).replace('<|im_end|>', '').replace('\r', '').split('\n\n')
        except KeyError as e:
            raise ValueError("预设不存在！")
        except FileNotFoundError as e:
            raise ValueError("预设文件不存在！")
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")

    OpenAI.update_forward_refs()
    @staticmethod
    def __load_json_config() -> Config:
        try:
            import json
            with open("config.json", "rb") as f:
                guessed_str = from_bytes(f.read()).best()
                if not guessed_str:
                    raise ValueError("无法识别 JSON 格式！")
                return Config.parse_obj(json.loads(str(guessed_str)))
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")
            exit(-1)


    @staticmethod
    def load_config() -> Config:
        try:
            import os
            if not (os.path.exists('config.cfg') and os.path.getsize('config.cfg') > 0) and os.path.exists('config.json'):
                logger.info("正在转换旧版配置文件……")
                Config.save_config(Config.__load_json_config())
                logger.warning("提示：配置文件已经修改为 config.cfg，原来的 config.json 将被重命名为 config.json.old。")
                try:
                    os.rename('config.json', 'config.json.old')
                except Exception as e:
                    logger.error(e)
                    logger.error("无法重命名配置文件，请自行处理。")
            with open("config.cfg", "rb") as f:
                guessed_str = from_bytes(f.read()).best()
                if not guessed_str:
                    raise ValueError("无法识别配置文件，请检查是否输入有误！")
                return Config.parse_obj(toml.loads(str(guessed_str)))
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")
            exit(-1)

    @staticmethod
    def save_config(config: Config) -> Config:
        try:
            with open("config.cfg", "wb") as f:
                parsed_str = toml.dumps(config.dict()).encode(sys.getdefaultencoding())
                f.write(parsed_str)
        except Exception as e:
                logger.exception(e)
                logger.warning("配置保存失败。")
