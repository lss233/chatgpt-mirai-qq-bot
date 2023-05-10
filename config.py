from __future__ import annotations
import contextlib
from typing import List, Union, Literal, Dict, Optional
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, BaseConfig, Extra, Field
from charset_normalizer import from_bytes
from loguru import logger
import os
import sys
import toml
import urllib.request

from framework.utils import network


class Onebot(BaseModel):
    manager_qq: int = Field(
        default=0,
        title="管理员 QQ",
        description="此 QQ 可以发送管理员命令"
    )


class Mirai(BaseModel):
    qq: int
    """Bot 的 QQ 号"""
    manager_qq: int = 0
    """机器人管理员的 QQ 号"""
    api_key: str = "1234567890"
    """mirai-api-http 的 verifyKey"""
    http_url: str = "http://localhost:8080"
    """mirai-api-http 的 http 适配器地址"""
    ws_url: str = "http://localhost:8080"
    """mirai-api-http 的 ws 适配器地址"""
    reverse_ws_host: str = "0.0.0.0"
    """mirai-api-http 的 反向 ws 主机号"""
    reverse_ws_port: Optional[int] = None
    """mirai-api-http 的 反向 ws 端口号，填写后开启 反向 ws 模式"""


class TelegramBot(BaseModel):
    bot_token: str = Field(
        description="从 BotFather 获取的机器人 Token"
    )
    """Bot 大爹给的 token"""
    proxy: Optional[str] = Field(
        title="代理地址",
        description="可选的代理地址，留空则检测系统代理",
        default=None
    )
    manager_chat: Optional[int] = Field(
        default=0,
        title="管理员 Chat ID",
        description="此 Chat ID 可以发送管理员命令"
    )


class DiscordBot(BaseModel):
    bot_token: str = Field(
        title="Bot Token",
        description="Discord Bot 的 token"
    )
    proxy: Optional[str] = Field(
        title="代理地址",
        description="可选的代理地址，留空则检测系统代理",
        default=None
    )


class HttpService(BaseModel):
    host: str = Field(
        title="Host",
        description="0.0.0.0则不限制访问地址",
        default="0.0.0.0"
    )
    port: int = Field(
        title="Port",
        description="Http service port, 默认8080",
        default=8080
    )
    debug: bool = Field(
        title="Debug",
        description="是否开启debug，错误时展示日志",
        default=False
    )
    password: Optional[str] = Field(
        title="登录密码",
        description="密码使用 SHA-512 哈希保存，如果未指定，则会在启动时随机生成一个密码。",
        default=None
    )


class WecomBot(BaseModel):
    host: str = Field(
        title="Host",
        description="企业微信回调地址，需要能够被公网访问，0.0.0.0则不限制访问地址",
        default="0.0.0.0"
    )
    port: int = Field(
        title="Port",
        description="Http service port, 默认5001",
        default=5001
    )
    debug: bool = Field(
        title="Debug",
        description="是否开启debug，错误时展示日志",
        default=False
    )
    corp_id: str = Field(
        title="企业 ID",
        description="企业微信 的 企业 ID",
    )
    agent_id: str = Field(
        title="Agent ID",
        description="企业微信应用 的 AgentId",
    )
    secret: str = Field(
        title="Secret",
        description="企业微信应用 的 Secret",
    )
    token: str = Field(
        title="Token",
        description="企业微信应用 API 令牌 的 Token",
    )
    encoding_aes_key: str = Field(
        title="Encoding AES Key",
        description="企业微信应用 API 令牌 的 EncodingAESKey",
    )


class OpenAIGPT3Params(BaseModel):
    temperature: float = Field(
        title="Temperature",
        description="温度参数，值在0到1之间，控制生成文本的多样性",
        default=0.5
    )
    max_tokens: int = Field(
        title="Max Tokens",
        description="生成文本的最大长度",
        default=4000
    )
    top_p: float = Field(
        title="Top-p",
        description="顶部概率值，控制生成文本的多样性",
        default=1.0
    )
    presence_penalty: float = Field(
        title="Presence Penalty",
        description="存在惩罚，控制生成文本重复度，值在0到1之间",
        default=0.0
    )
    frequency_penalty: float = Field(
        title="Frequency Penalty",
        description="频率惩罚，控制生成文本重复度，值在0到1之间",
        default=0.0
    )
    min_tokens: int = Field(
        title="Min Tokens",
        description="生成文本的最小长度",
        default=1000
    )


class OpenAIAuths(BaseModel):
    browserless_endpoint: Optional[str] = "https://chatgpt-proxy.lss233.com/api/"
    """自定义无浏览器登录模式的接入点"""
    api_endpoint: Optional[str] = None
    """自定义 OpenAI API 的接入点"""

    gpt3_params: OpenAIGPT3Params = OpenAIGPT3Params()

    accounts: List[Union[OpenAIEmailAuth, OpenAISessionTokenAuth, OpenAIAccessTokenAuth, OpenAIAPIKey]] = []


class OpenAIAuthBase(BaseModel):
    mode: str = "browserless"
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
    gpt4: bool = False
    """使用 GPT-4"""
    model: Optional[str] = None
    """使用的默认模型，此选项优先级最高"""
    verbose: bool = False
    """启用详尽日志模式"""
    title_pattern: str = ""
    """自动修改标题，为空则不修改"""
    auto_remove_old_conversations: bool = False
    """自动删除旧的对话"""

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


class PoeCookieAuth(BaseModel):
    p_b: str
    """登陆 poe.com 后 Cookie 中 p_b 的值"""
    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""


class BingCookiePath(BaseModel):
    cookie_content: str
    """Bing 的 Cookie 文件内容"""
    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""


class BardCookiePath(BaseModel):
    cookie_content: str
    """Bard 的 Cookie 文件内容"""
    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""


class PoeAuths(BaseModel):
    accounts: List[PoeCookieAuth] = []
    """Poe 的账号列表"""


class TTSAccounts(BaseModel):
    speech_key: str
    """TTS KEY"""
    speech_service_region: str
    """TTS 地区"""
    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""


class BingAuths(BaseModel):
    show_suggestions: bool = True
    """在 Bing 的回复后加上猜你想问"""
    show_references: bool = True
    """在 Bing 的回复前加上引用资料"""
    show_remaining_count: bool = True
    """在 Bing 的回复后加上剩余次数"""

    use_drawing: bool = False
    """使用 Bing 画图"""

    wss_link: str = "wss://sydney.bing.com/sydney/ChatHub"
    """Bing 的 Websocket 接入点"""
    bing_endpoint: str = "https://edgeservices.bing.com/edgesvc/turing/conversation/create"
    """Bing 的会话创建接入点"""
    accounts: List[BingCookiePath] = []
    """Bing 的账号列表"""
    max_messages: int = 20
    """Bing 的最大消息数，仅展示用"""


class BardAuths(BaseModel):
    accounts: List[BardCookiePath] = []
    """Bard 的账号列表"""


class YiyanCookiePath(BaseModel):
    BDUSS: Optional[str] = None
    """百度 Cookie 中的 BDUSS 字段"""
    BAIDUID: Optional[str] = None
    """百度 Cookie 中的 BAIDUID 字段"""
    cookie_content: Optional[str] = None
    """百度 Cookie （已弃用）"""
    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""


class YiyanAuths(BaseModel):
    accounts: List[YiyanCookiePath] = []
    """文心一言的账号列表"""


class ChatGLMAPI(BaseModel):
    api_endpoint: str
    """自定义 ChatGLM API 的接入点"""
    max_turns: int = 10
    """最大对话轮数"""
    timeout: int = 120
    """请求超时时间（单位：秒）"""


class ChatGLMAuths(BaseModel):
    accounts: List[ChatGLMAPI] = []
    """ChatGLM的账号列表"""


class SlackAppAccessToken(BaseModel):
    channel_id: str
    """负责与机器人交互的 Channel ID"""

    access_token: str
    """安装 Slack App 时获得的 access_token"""

    proxy: Optional[str] = None
    """可选的代理地址，留空则检测系统代理"""

    app_endpoint: str = "https://chatgpt-proxy.lss233.com/claude-in-slack/backend-api/"
    """API 的接入点"""


class SlackAuths(BaseModel):
    accounts: List[SlackAppAccessToken] = []
    """Slack App 账号信息"""


class TextToImage(BaseModel):
    always: bool = Field(
        title="强制开启",
        description="是否强制开启，设置后所有的会话强制以图片发送",
        default=False
    )
    default: bool = Field(
        title="默认开启",
        description="设置后新会话默认以图片模式发送",
        default=False
    )
    font_size: int = Field(
        title="Font Size",
        description="字号",
        default=30
    )
    width: int = Field(
        title="Width",
        description="生成图片宽度",
        default=1000
    )
    font_path: str = Field(
        title="Font Path",
        description="字体路径",
        default="fonts/sarasa-mono-sc-regular.ttf"
    )
    offset_x: int = Field(
        title="Offset X",
        description="横坐标",
        default=50
    )
    offset_y: int = Field(
        title="Offset Y",
        description="纵坐标",
        default=50
    )
    wkhtmltoimage: Optional[str] = Field(
        title="wkhtmltoimage",
        description="wkhtmltoimage 程序路径，留空则自动检测",
        default=None
    )


class TextToSpeech(BaseModel):
    always: bool = Field(
        title="强制开启",
        description="设置后所有的会话都会转语音再发一次",
        default=False
    )
    engine: str = Field(
        title="引擎",
        description="文字转语音引擎选择",
        default="azure"
    )
    default: str = Field(
        title="默认音色",
        description="你可以在[这里](https://learn.microsoft.com/zh-CN/azure/cognitive-services/speech-service/language-support?tabs=tts#neural-voices)查看支持的音色列表",
        default="zh-CN-XiaoxiaoNeural"
    )
    default_voice_prefix: List[str] = Field(
        title="Default Voice Prefix",
        description="默认的提示音色前缀",
        default=["zh-CN", "zh-TW"]
    )


class AzureConfig(BaseModel):
    tts_speech_key: Optional[str] = Field(
        title="TTS Speech Key",
        description="TTS KEY",
        default=None
    )
    tts_speech_service_region: Optional[str] = Field(
        title="TTS Speech Service Region",
        description="TTS 地区",
        default=None
    )


class VitsConfig(BaseModel):
    api_url: str = Field(
        title="API URL",
        description="VITS API 地址，目前仅支持基于MoeGoe的API",
        default=""
    )
    lang: str = Field(
        title="Language",
        description="VITS_API目标语言",
        default="zh"
    )
    speed: float = Field(
        title="Speech Speed",
        description="VITS语言语速",
        default=1.4
    )
    timeout: int = Field(
        title="Timeout",
        description="语音生成超时时间",
        default=30
    )


class Trigger(BaseModel):
    prefix: List[str] = Field(
        default=[""],
        title="全局触发响应前缀",
        description="同时适用于私聊和群聊，默认不需要"
    )
    prefix_friend: List[str] = Field(
        default=[],
        title="私聊触发响应前缀",
        description="默认不需要"
    )
    prefix_group: List[str] = Field(
        default=[],
        title="群聊触发响应前缀",
        description="默认不需要"
    )

    prefix_ai: Dict[str, List[str]] = Field(
        default={},
        title="特定类型 AI 的前缀",
        description="以此前缀开头将直接发消息至指定 AI 会话"
    )

    require_mention: Literal["at", "mention", "none"] = Field(
        default="at",
        title="群内是否需要 @ 机器人",
        description="选项：  \n * at - 需要 @ 机器人  \n * mention=需要 @ 或以机器人名称开头  \n * none=不需要 [@] 才响应  \n\n请注意，设置后需要先 @ 机器人后接前缀"
    )

    reset_command: List[str] = Field(
        default=["重置会话"],
        title="重置会话命令"
    )

    rollback_command: List[str] = Field(
        default=["回滚会话"],
        title="回滚会话命令"
    )

    prefix_image: List[str] = Field(
        default=["画", "看"],
        title="图片创建前缀"
    )

    switch_model: str = Field(
        default=r"切换模型 (.+)",
        title="切换模型命令"
    )

    switch_command: str = Field(
        default=r"切换AI (.+)",
        title="切换AI命令"
    )

    switch_voice: str = Field(
        default=r"切换语音 (.+)",
        title="切换语音命令"
    )

    mixed_only_command: List[str] = Field(
        default=["图文混合模式"],
        title="图文混合模式命令"
    )

    image_only_command: List[str] = Field(
        default=["图片模式"],
        title="图片模式命令"
    )

    text_only_command: List[str] = Field(
        default=["文本模式"],
        title="文本模式命令"
    )

    ignore_regex: List[str] = Field(
        default=[],
        title="忽略正则表达式"
    )

    allowed_models: List[str] = Field(
        default=[
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0301",
            "text-davinci-002-render-sha",
            "text-davinci-002-render-paid"
        ],
        title="允许切换的模型列表"
    )

    allow_switching_ai: bool = Field(
        default=True,
        title="是否允许普通用户切换AI"
    )

    ping_command: List[str] = Field(
        default=["ping"],
        title="查询机器人状态的命令"
    )


class Response(BaseModel):
    mode: str = Field(
        title="响应模式",
        description="支持：mixed - 图文混合, force-text  - 仅文字, force-image - 仅图片",
        default="mixed"
    )

    buffer_delay: float = Field(
        title="分段回复缓存时长",
        description="设置分段回复缓存时长（秒），开启后机器人会分段进行回复",
        default=15
    )

    default_ai: Optional[str] = Field(
        title="默认使用的 AI 类型",
        description="不填写时自动推测",
        default=None
    )

    error_format: str = Field(
        title="出错时发送的消息",
        description="发生错误时发送的消息，请注意可以插入 {exc} 作为异常占位符",
        default="出现故障！如果这个问题持续出现，请和我说“重置会话” 来开启一段新的会话，或者发送 “回滚对话” 来回溯到上一条对话，你上一条说的我就当作没看见。\n原因：{exc}"
    )

    error_network_failure: str = Field(
        title="网络故障时的消息",
        description="发生网络错误时发送的消息，请注意可以插入 {exc} 作为异常占位符",
        default="网络故障！连接服务器失败，我需要更好的网络才能服务！\n{exc}"
    )

    error_session_authenciate_failed: str = Field(
        title="身份验证失败时的消息",
        description="发生网络错误时发送的消息，请注意可以插入 {exc} 作为异常占位符",
        default="身份验证失败！无法登录至 ChatGPT 服务器，请检查账号信息是否正确！\n{exc}"
    )

    error_request_too_many: str = Field(
        title="请求过多时的消息",
        description="糟糕！当前收到的请求太多了，我需要一段时间冷静冷静。你可以选择“重置会话”，或者过一会儿再来找我！\n预计恢复时间：{exc}\n",
        default="糟糕！当前收到的请求太多了，我需要一段时间冷静冷静。你可以选择“重置会话”，或者过一会儿再来找我！\n预计恢复时间：{exc}\n"
    )

    error_request_concurrent_error: str = Field(
        title="并发错误时的消息",
        description="当前有其他人正在和我进行聊天，请稍后再给我发消息吧！",
        default="当前有其他人正在和我进行聊天，请稍后再给我发消息吧！"
    )

    error_server_overloaded: str = Field(
        title="服务器过载时的消息",
        description="服务器提示 429 错误时的回复 ",
        default="抱歉，当前服务器压力有点大，请稍后再找我吧！"
    )

    error_drawing: str = Field(
        title="画图失败时的消息",
        description="画图失败！原因： {exc}",
        default="画图失败！原因： {exc}"
    )

    placeholder: str = Field(
        title="空消息回复占位符",
        description="对空消息回复的占位符",
        default="您好！我是 Assistant，一个由 OpenAI 训练的大型语言模型。我不是真正的人，而是一个计算机程序，可以通过文本聊天来帮助您解决问题。如果您有任何问题，请随时告诉我，我将尽力回答。\n如果您需要重置我们的会话，请回复`重置会话`。"
    )

    reset: str = Field(
        title="重置会话时的消息",
        description="重置会话时发送的消息",
        default="会话已重置。"
    )

    rollback_success: str = Field(
        title="回滚成功时的消息",
        description="成功回滚时发送的消息",
        default="已回滚至上一条对话，你刚刚发的我就忘记啦！"
    )

    rollback_fail: str = Field(
        title="回滚失败时的消息",
        description="回滚失败时发送的消息",
        default="回滚失败，没有更早的记录了！如果你想要重新开始，请发送：{reset}"
    )

    quote: bool = Field(
        title="是否回复触发的消息",
        description="是否回复触发的那条消息",
        default=True
    )

    timeout: float = Field(
        title="响应时间",
        description="发送提醒前允许的响应时间",
        default=30.0
    )

    timeout_format: str = Field(
        title="响应时间过长时的消息",
        description="响应时间过长时要发送的提醒",
        default="我还在思考中，请再等一下~"
    )

    max_timeout: float = Field(
        title="最长等待时间",
        description="最长等待时间，超过此时间取消回应",
        default=600.0
    )

    cancel_wait_too_long: str = Field(
        title="等待时间过长时的消息",
        description="发送提醒前允许的响应时间",
        default="啊哦，这个问题有点难，让我想了好久也没想明白。试试换个问法？"
    )

    max_queue_size: int = Field(
        title="等待处理的消息的最大数量",
        description="如果要关闭此功能，设置为 0",
        default=10
    )

    queue_full: str = Field(
        title="队列满时的提示",
        description="队列满时的提示",
        default="抱歉！我现在要回复的人有点多，暂时没有办法接收新的消息了，请过会儿再给我发吧！"
    )

    queued_notice_size: int = Field(
        title="新消息通知的长度最小值",
        description="新消息加入队列会发送通知的长度最小值",
        default=3
    )

    queued_notice: str = Field(
        title="新消息进入队列时的通知",
        description="新消息进入队列时，发送的通知。 queue_size 是当前排队的消息数",
        default="消息已收到！当前我还有{queue_size}条消息要回复，请您稍等。"
    )

    ping_response: str = Field(
        title="ping返回内容",
        description="ping返回内容",
        default="当前AI：{current_ai} / 当前语音：{current_voice}\n指令：\n切换AI XXX / 切换语音 XXX\n\n可用AI：\n{supported_ai}"
    )

    ping_tts_response: str = Field(
        title="ping tts 返回内容",
        description="ping tts 返回内容",
        default="\n可用语音：\n{supported_tts}"
    )


class System(BaseModel):
    proxy: Optional[str] = Field(
        title="代理服务器地址",
        description="不填则使用系统设置",
        default=None
    )
    use_system_proxy: bool = Field(
        title="使用系统代理设置",
        description="",
        default=False
    )
    accept_group_invite: bool = Field(
        title="自动接收邀请入群请求",
        description="",
        default=False
    )
    accept_friend_request: bool = Field(
        title="自动接收好友请求",
        description="",
        default=False
    )


class BaiduCloud(BaseModel):
    check: bool = Field(
        title="启动百度云内容安全审核",
        description="",
        default=False
    )
    baidu_api_key: str = Field(
        title="百度云API_KEY",
        description="24位英文数字字符串",
        default=""
    )
    baidu_secret_key: str = Field(
        title="百度云SECRET_KEY",
        description="32位的英文数字字符串",
        default=""
    )
    prompt_message: str = Field(
        title="不合规消息自定义返回",
        description="[百度云]请珍惜机器人，当前返回内容不合规",
        default="[百度云]请珍惜机器人，当前返回内容不合规"
    )


class Prompt(BaseModel):
    command: str = Field(
        title="加载预设命令",
        description=r"加载预设 (\w+)",
        default=r"加载预设 (\w+)"
    )
    keywords: dict[str, str] = Field(
        title="关键词",
        description="",
        default={}
    )
    loaded_successful: str = Field(
        title="预设加载成功消息",
        description="预设加载成功！",
        default="预设加载成功！"
    )
    scan_dir: str = Field(
        title="预设文件夹路径",
        description="./prompts",
        default="./prompts"
    )
    hide: bool = Field(
        title="禁止使用其他人 .预设列表",
        description="是否禁止使用其他人 .预设列表 命令来查看预设",
        default=False
    )


class Ratelimit(BaseModel):
    warning_rate: float = Field(
        title="额度使用警告比例",
        description="额度使用达到此比例时进行警告",
        default=0.8
    )
    warning_msg: str = Field(
        title="额度警告消息",
        description="\n\n警告：额度即将耗尽！\n目前已发送：{usage}条消息，最大限制为{limit}条消息/小时，请调整您的节奏。\n额度限制整点重置，当前服务器时间：{current_time}",
        default="\n\n警告：额度即将耗尽！\n目前已发送：{usage}条消息，最大限制为{limit}条消息/小时，请调整您的节奏。\n额度限制整点重置，当前服务器时间：{current_time}"
    )
    exceed: str = Field(
        title="额度超限消息",
        description="已达到额度限制，请等待下一小时继续和我对话。",
        default="已达到额度限制，请等待下一小时继续和我对话。"
    )
    draw_warning_msg: str = Field(
        title="画图额度警告消息",
        description="\n\n警告：额度即将耗尽！\n目前已画：{usage}个图，最大限制为{limit}个图/小时，请调整您的节奏。\n额度限制整点重置，当前服务器时间：{current_time}",
        default="\n\n警告：额度即将耗尽！\n目前已画：{usage}个图，最大限制为{limit}个图/小时，请调整您的节奏。\n额度限制整点重置，当前服务器时间：{current_time}"
    )
    draw_exceed: str = Field(
        title="画图额度超限消息",
        description="已达到额度限制，请等待下一小时再使用画图功能。",
        default="已达到额度限制，请等待下一小时再使用画图功能。"
    )


class SDWebUIParams(BaseModel):
    api_url: str = Field(
        title="API 基地址",
        description="如：http://127.0.0.1:7890"
    )
    prompt_prefix: str = Field(
        title="内置提示词",
        description="所有的画图内容都会加上这些提示词",
        default="masterpiece, best quality, illustration, extremely detailed 8K wallpaper"
    )
    negative_prompt: str = Field(
        title="负面提示词",
        description="",
        default="NG_DeepNegative_V1_75T, badhandv4, EasyNegative, bad hands, missing fingers, cropped legs, worst quality, low quality, normal quality, jpeg artifacts, blurry,missing arms, long neck, Humpbacked,multiple breasts, mutated hands and fingers, long body, mutation, poorly drawn , bad anatomy,bad shadow,unnatural body, fused breasts, bad breasts, more than one person,wings on halo,small wings, 2girls, lowres, bad anatomy, text, error, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, username, out of frame, lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, nsfw, nake, nude, blood"
    )
    sampler_index: str = Field(
        title="采样器索引",
        description="",
        default="DPM++ SDE Karras"
    )
    filter_nsfw: bool = Field(
        title="过滤 NSFW",
        description="",
        default=True
    )
    denoising_strength: float = Field(
        title="去噪强度",
        description="",
        default=0.45
    )
    steps: int = Field(
        title="步数",
        description="",
        default=25
    )
    enable_hr: bool = Field(
        title="启用高分辨率",
        description="",
        default=False
    )
    seed: int = Field(
        title="随机数种子",
        description="",
        default=-1
    )
    batch_size: int = Field(
        title="批次大小",
        description="",
        default=1
    )
    n_iter: int = Field(
        title="迭代次数",
        description="",
        default=1
    )
    cfg_scale: float = Field(
        title="配置比例",
        description="",
        default=7.5
    )
    restore_faces: bool = Field(
        title="修复面部",
        description="",
        default=False
    )
    authorization: str = Field(
        title="登录API的账号:密码",
        description=""
    )
    timeout: float = Field(
        title="超时时间",
        description="",
        default=10.0
    )

    class Config(BaseConfig):
        extra = Extra.allow


class AccountsModel(BaseModel):
    """记录各种账号信息"""
    pass


class Config(BaseModel):
    # === Platform Settings ===
    onebot: Optional[Onebot] = None
    mirai: Optional[Mirai] = None
    telegram: Optional[TelegramBot] = None
    discord: Optional[DiscordBot] = None
    http: Optional[HttpService] = None
    wecom: Optional[WecomBot] = None

    # === Account Settings ===
    accounts: AccountsModel = AccountsModel()

    openai: OpenAIAuths = OpenAIAuths()
    bing: BingAuths = BingAuths()
    bard: BardAuths = BardAuths()
    azure: AzureConfig = AzureConfig()
    yiyan: YiyanAuths = YiyanAuths()
    chatglm: ChatGLMAuths = ChatGLMAuths()
    poe: PoeAuths = PoeAuths()
    slack: SlackAuths = SlackAuths()

    # === Response Settings ===
    text_to_image: TextToImage = TextToImage()
    text_to_speech: TextToSpeech = TextToSpeech()
    trigger: Trigger = Trigger()
    response: Response = Response()
    system: System = System()
    prompts: Prompt = Prompt()
    ratelimit: Ratelimit = Ratelimit()
    baiducloud: BaiduCloud = BaiduCloud()
    vits: VitsConfig = VitsConfig()

    # === External Utilities ===
    sdwebui: Optional[SDWebUIParams] = None

    def scan_prompts(self):
        for keyword, path in self.prompts.keywords.items():
            if os.path.isfile(path):
                logger.success(f"检查预设：{keyword} <==> {path} [成功]")
            else:
                logger.error(f"检查预设：{keyword} <==> {path} [失败：文件不存在]")
        for root, _, files in os.walk(self.prompts.scan_dir, topdown=False):
            for name in files:
                if not name.endswith(".yml") and not name.endswith(".yaml"):
                    continue
                path = os.path.join(root, name)
                name = name.removesuffix('.yml').removesuffix(".yaml")
                if name in self.prompts.keywords:
                    logger.error(f"注册预设：{name} <==> {path} [失败：关键词已存在]")
                    continue
                self.prompts.keywords[name] = path
                logger.success(f"注册预设：{name} <==> {path} [成功]")

    def load_preset(self, keyword):
        try:
            with open(self.prompts.keywords[keyword], "rb") as f:
                if guessed_str := from_bytes(f.read()).best():
                    return str(guessed_str).replace('<|im_end|>', '').replace('\r', '').split('\n\n')
                else:
                    raise ValueError("无法识别预设的 JSON 格式，请检查编码！")

        except KeyError as e:
            raise ValueError("预设不存在！") from e
        except FileNotFoundError as e:
            raise ValueError("预设文件不存在！") from e
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")

    OpenAIAuths.update_forward_refs()

    @staticmethod
    def __load_json_config() -> Config:
        try:
            import json
            with open("config.json", "rb") as f:
                if guessed_str := from_bytes(f.read()).best():
                    return Config.parse_obj(json.loads(str(guessed_str)))
                else:
                    raise ValueError("无法识别 JSON 格式！")
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")
            exit(-1)

    @staticmethod
    def load_config() -> Config:
        if env_config := os.environ.get('CHATGPT_FOR_BOT_FULL_CONFIG', ''):
            return Config.parse_obj(toml.loads(env_config))
        try:
            if (
                    not os.path.exists('config.cfg')
                    or os.path.getsize('config.cfg') <= 0
            ) and os.path.exists('config.json'):
                logger.info("正在转换旧版配置文件……")
                Config.save_config(Config.__load_json_config())
                logger.warning("提示：配置文件已经修改为 config.cfg，原来的 config.json 将被重命名为 config.json.old。")
                try:
                    os.rename('config.json', 'config.json.old')
                except Exception as e:
                    logger.error(e)
                    logger.error("无法重命名配置文件，请自行处理。")
            with open("config.cfg", "rb") as f:
                if guessed_str := from_bytes(f.read()).best():
                    return Config.parse_obj(toml.loads(str(guessed_str)))
                else:
                    raise ValueError("无法识别配置文件，请检查是否输入有误！")
        except Exception as e:
            logger.exception(e)
            logger.error("配置文件有误，请重新修改！")
            exit(-1)

    @staticmethod
    def save_config(config: Config):
        try:
            with open("config.cfg", "wb") as f:
                parsed_str = toml.dumps(config.dict()).encode(sys.getdefaultencoding())
                f.write(parsed_str)
        except Exception as e:
            logger.exception(e)
            logger.warning("配置保存失败。")

    @staticmethod
    def __setup_system_proxy():
        for url in urllib.request.getproxies().values():
            return url

    def check_proxy(self):
        if self.system.proxy is None and self.system.use_system_proxy:
            self.__setup_system_proxy()

        if self.system.proxy is None:
            return None

        logger.info(f"[代理测试] 正在检查代理配置：{self.system.proxy}")
        proxy_addr = urlparse(self.system.proxy)
        if not network.is_open(proxy_addr.hostname, proxy_addr.port):
            raise ValueError("无法连接至本地代理服务器，请检查配置文件中的 proxy 是否正确！")
        requests.get("http://www.gstatic.com/generate_204", proxies={
            "https": self.system.proxy,
            "http": self.system.proxy
        })
        logger.success("[代理测试] 连接成功！")
        return self.system.proxy
