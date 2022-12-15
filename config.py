from __future__ import annotations
from typing import List, Union, Literal
from pydantic import BaseModel, BaseConfig, Extra, Field
from charset_normalizer import from_bytes
from loguru import logger
import sys
import json


class Mirai(BaseModel):
    qq: int
    """Bot 的 QQ 号"""
    api_key: str
    """mirai-api-http 的 verifyKey"""
    http_url: str = "http://localhost:8080"
    """mirai-api-http 的 http 适配器地址"""
    ws_url: str = "http://localhost:8080"
    """mirai-api-http 的 ws 适配器地址"""

class OpenAIAuthBase(BaseModel):
    Authorization: Union[str, None] = Field(alias="authorization")
    """可选的验证头"""
    proxy: Union[str, None] = None
    """可选的代理地址"""
    base_url: str = "https://chat.openai.com/"
    """OpenAI 地址，可以填入反向代理"""

    cf_clearance: Union[str, None] = None
    """CloudFlare 验证 cookie"""

    user_agent: Union[str, None] = None
    """访问 OpenAI 使用的浏览器 UserAgent"""

    class Config(BaseConfig):
        extra = Extra.allow

class OpenAIEmailAuth(OpenAIAuthBase):
    email: str
    """OpenAI 注册邮箱"""
    password: str
    """OpenAI 密码"""

class OpenAISessionTokenAuth(OpenAIAuthBase):
    session_token: str
    """OpenAI 的 session_token"""

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

class System(BaseModel):
    auto_save_cf_clearance: bool = True
    """自动保存 cf_clearance"""

    auto_save_session_token: bool = False
    """自动保存 session_token"""

    accept_group_invite: bool = False
    """自动接收邀请入群请求"""

    accept_friend_request: bool = False
    """自动接收好友请求"""

class Config(BaseModel):
    mirai: Mirai
    openai: Union[OpenAIEmailAuth, OpenAISessionTokenAuth]
    text_to_image: TextToImage = TextToImage()
    trigger: Trigger = Trigger()
    response: Response = Response()
    system: System = System()

    @staticmethod
    def load_config() -> Config:
        try:
            with open("config.json", "rb") as f:
                guessed_json = from_bytes(f.read()).best()
                if not guessed_json:
                    raise ValueError("无法识别 JSON 格式！")
                
                return Config.parse_obj(json.loads(str(guessed_json)))
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")
            exit(-1)

    @staticmethod
    def save_config(config: Config) -> Config:
        if config.system.auto_save_cf_clearance or config.system.auto_save_session_token:
            try:
                with open("config.json", "rb") as f:
                    guessed_json = from_bytes(f.read()).best()
                with open("config.json", "wb") as f:
                    logger.debug(f"配置文件编码 {guessed_json.encoding} {config.response.timeout_format}")
                    parsed_json = json.dumps(config.dict(), ensure_ascii=False, indent=4).encode(sys.getdefaultencoding())
                    f.write(parsed_json)
            except Exception as e:
                    logger.exception(e)
                    logger.warning("配置保存失败。")
