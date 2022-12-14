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
* [x] 多种方式登录 OpenAI
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
        "session_token": "SESSION_TOKEN", // 你的 OpenAI 的 session_token，详见下
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
    }
```

### Session 登录

指定 `session_token` 手动登录是**最简单直接**的登录方式，大概率能解决`Captcha detect`、 `State not found` 等各种问题：

```jsonc
    // 前面别的东西
    "openai": {
        "session_token": "一串ey开头的很长的东西..." // 注意， ey 开头的可能有两个，别复制错了！
    },
    // 后面别的东西
```

请参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup) 了解 `session_token` 的获取方法。

如果你看见 `Exception: Wrong response code` 的错误，说明你的 `session_token` 过期了或者不正确。`session_token` 具有时效性，如果长期出现错误的情况，请重新获取你的  `session_token`。 [#29](https://github.com/lss233/chatgpt-mirai-qq-bot/issues/29)

### OpenAI 邮箱密码登录

支持使用 OpenAI 邮箱、密码的方式登录。  

在启动时，我们会打开一个浏览器，   

当你使用这种方式登录时，需要在打开的浏览器页面中完成 OpenAI 的登录。  

我们会自动点击页面中的 `Log in` 按钮、为您填写 `email`，剩下的需要您自己完成。

登录完成后，浏览器会自动退出。

```jsonc
    // 前面别的东西
    "openai": {
        "email": "你的邮箱",
        "password": "随便填"
    },
    // 后面别的东西
```

#### 使用第三方服务自动填写验证码

我们的依赖 revChatGPT 支持通过第三方服务 [2Captcha](https://2captcha.com?from=16366923) 
来实现自动填写验证码，如果您愿意使用这种方式，可以填写 2Chaptcha 的 API 密钥来开启这一功能。

提示：这需要您向他们（2Captcha）支付一些费用。


```jsonc
    // 前面别的东西
    "openai": {
        "email": "你的邮箱",
        "password": "你的密码",
        "captcha": "2Captcha 的 API Key",
    },
    // 后面别的东西
```

### 微软账号登录

支持使用微软账号登录：

```jsonc
    // 前面别的东西
    "openai": {
        "email": "你的微软账号邮箱",
        "password": "你的微软账号密码",
        "isMicrosoftLogin": true
    },
    // 后面别的东西
```

### 使用正向代理

如果你的网络访问 OpenAI 比较慢，或者你的 IP 被封锁了，可以通过配置代理的方式来连接到 OpenAI。支持使用正向代理方式访问 OpenAI，你需要一个 HTTTP/HTTPS 代理服务器：

```jsonc
    // 前面别的东西
    "openai": {
        // 在前面提及的登录方式中选一种，然后加上 proxy，填写你的代理服务器地址。别忘了处理 json 逗号
        "proxy": "http://localhost:1080"
    },
    // 后面别的东西
```

### 自定义人格

我们现在支持在会话的初始阶段为机器人设置人格。  

请查阅 `chatbot.py` 中的 `initial_process` 和 `keyword_presets_process` 方法，了解如何设置。

## 📷 图片转文字

向 QQ 群发送消息失败时，自动将消息转为图片发送。  

字体文件存放于 `fonts/` 目录中。  

默认使用的字体是 [更纱黑体](https://github.com/be5invis/Sarasa-Gothic)。  
