# ChatGPT Mirai QQ Bot

**一款使用 OpenAI 的 ChatGPT 进行聊天的 QQ 机器人！**

***

基于：
 - [Ariadne](https://github.com/GraiaProject/Ariadne)
 - [mirai-http-api](https://github.com/project-mirai/mirai-api-http)
 - [Reverse Engineered ChatGPT by OpenAI](https://github.com/acheong08/ChatGPT).  

支持：  
* [x] 文字转图片发送  
* [x] 群聊回复引用
* [x] 关键词触发回复
* [x] 正向代理
* [x] 无需浏览器登录
* [x] 预设人格初始化


[交流群](https://jq.qq.com/?_wv=1027&k=3X55LqoY) 遇到问题请发日志和配置文件  
[调试群](https://jq.qq.com/?_wv=1027&k=TBX8Saq7) 本群不解答技术问题  

![Preview](.github/preview.png)


## 🔧 使用

<details>
    <summary>Linux: 通过 Docker Compose 部署 （自带 Mirai, 新人推荐)</summary>

我们使用 `docker-compose.yaml` 整合了 [ttionya/mirai-http](https://github.com/ttionya/mirai-http-docker) 和本项目来实现快速部署。  

但是在部署过程中仍然需要一些步骤来进行配置。  

您可以尝试使用  [@paradox8599](https://github.com/paradox8599) 提供的简易部署脚本：[paradox8599/mirai-chatgpt-setup](https://github.com/paradox8599/mirai-chatgpt-setup) 进行较快地部署。  

**或者**移步至 [Wiki](https://github.com/lss233/chatgpt-mirai-qq-bot/wiki/%E4%BD%BF%E7%94%A8-Docker-Compose-%E9%83%A8%E7%BD%B2%EF%BC%88Mirai---%E6%9C%AC%E9%A1%B9%E7%9B%AE%EF%BC%89) 浏览手工配置的方案。

</details>

<details>
    <summary>Linux: 通过 Docker 部署 （适合已经有 Mirai 的用户)</summary>

1. 找个合适的位置，写你的 `config.json`。

2.  执行以下命令，启动 bot：
```bash
# 修改 /path/to/config.json 为你 config.json 的位置
# XPRA_PASSWORD=123456 中的 123456 是你的 Xpra 密码，建议修改
docker run --name mirai-chatgpt-bot \
    -e XPRA_PASSWORD=123456 \ 
    -v /path/to/config.json:/app/config.json \
    --network host \
    lss233/chatgpt-mirai-qq-bot:latest
```

3. 启动后，在浏览器访问 `http://你的服务器IP:14500` 可以访问到登录 ChatGPT 的浏览器页面  

</details>

<details>
    <summary>Windows: 快速部署包 (自带 Mirai，新人推荐）</summary>

我们为 Windows 用户制作了一个快速启动包，可以在 [Release](https://github.com/lss233/chatgpt-mirai-qq-bot/releases) 中找到。    

文件名为：`quickstart-windows-amd64.zip`  
</details>

<details>
    <summary>手动部署</summary>

提示：你需要 Python >= 3.9 才能运行本项目  

1. 部署 Mirai ，安装 mirai-http-api 插件。

2. 下载本项目:
```bash
git clone https://github.com/lss233/chatgpt-mirai-qq-bot
cd chatgpt-mirai-qq-bot
pip3 install -r requirements.txt
```

3. 参照下文调整配置文件。


4. 启动 bot.
```bash
python3 bot.py
```
</details>



## ⚙ 配置文件

参考 `config.example.json` 调整配置文件。将其复制为 `config.json`，然后修改 `config.json`。

配置文件主要包含 mirai-http-api 的连接信息和 OpenAI 的登录信息。

OpenAI 注册教程： https://www.cnblogs.com/mrjade/p/16968591.html  

OpenAI 配置的信息可参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup)。

**！！请注意！！ 不要把 `//` 开头的注释也抄进去了！**  

```jsonc
{
    "mirai": {
        "qq": 123456, // 机器人的 QQ 账号
        "api_key": "VERIFY_KEY", // mirai-http-api 中的 verifyKey
        "http_url": "http://localhost:8080", // mirai-http-api 中的 http 回调地址
        "ws_url": "http://localhost:8080" // mirai-http-api 中的 ws 回调地址
    },
    "openai": {
        "api_key": "sk-xxxxxxx", // 你的 OpenAI 的 api_key，详见下
    },
    "text_to_image": { // 文字转图片
        "font_size": 30, // 字体大小
        "width": 700, // 图片宽度
        "font_path": "fonts/sarasa-mono-sc-regular.ttf", // 字体
        "offset_x": 50, // 起始点 X
        "offset_y": 50 // 起始点 Y
    },
    "trigger": { // 配置机器人要如何响应，下面所有项均可选 (也就是可以直接删掉那一行)
        "prefix": ["/chat", "#chat"], // 符合前缀才会响应，可以自己增减
        "require_mention": "at", // 配置群里如何让机器人响应，"at" 表示需要群里 @ 机器人，"mention" 表示 @ 或者以机器人名字开头都可以，"none" 表示不需要
        "reset_command": ["重置会话", "/reset"], // 重置会话的命令
        "rollback_command": ["回滚对话", "/rollback"] // 回滚会话的命令
    },
    "response": {
        "placeholder": "您好！我是 Assistant...", // 匹配指令成功但没有对话内容时发送的消息
        "reset": "会话已重置~", // 重置会话时发送的消息
        "rollback_success": "已回滚至上一条对话 OwO", // 回滚成功时发送的消息
        "rollback_fail": "回滚失败 >_<", // 回滚失败时发送的消息
        "error_format": "发生错误了...\n{exc}", // 发生错误时要发送的消息
        "quote": true, // 是否要回复触发指令的消息
        "timeout": 30, // 发送下面那个提醒之前的等待时间
        "timeout_format": "我还在思考中，请再等一下~" // 超过响应时间时要发送的提醒
    },
    "system": {
        "accept_friend_request": false, // 是否自动接受好友请求
        "accept_group_invite": false // 是否自动接受加群邀请
    },
    "presets": {
        "keywords": {
            "正常": "presets/default.txt",  // 预设名称 <-> 预设对应的聊天记录
            "猫娘": "presets/catgirl.txt"
        }
    }
}
```

### API Key 登录

截止至 2023年2月3日， OpenAI 可以通过 API Key 的方式**免费**使用 ChatGPT，无需浏览器、无访问限制。  

你可以在[这里](https://platform.openai.com/account/api-keys)生成 API Key。

```jsonc
    // 前面别的东西
    "openai": {
        "session_token": "一串sk-开头的东西..."
    },
    // 后面别的东西
```

### 加载预设

如果你想让机器人自动带上某种聊天风格，可以使用预设功能。  

我们自带了 `猫娘` 和 `正常` 两种预设，你可以在 `presets` 文件夹下了解预设的写法。  

使用 `加载预设 猫娘` 来加载猫娘预设。

你可以参考[Awesome-ChatGPT-prompts-ZH_CN](https://github.com/L1Xu4n/Awesome-ChatGPT-prompts-ZH_CN) 来调教你的 ChatGPT。

## 📷 图片转文字

向 QQ 群发送消息失败时，自动将消息转为图片发送。  

字体文件存放于 `fonts/` 目录中。  

默认使用的字体是 [更纱黑体](https://github.com/be5invis/Sarasa-Gothic)。  
