# ChatGPT Mirai QQ Bot

**一款使用 OpenAI 的 ChatGPT 进行聊天的 QQ 机器人！**


> **2023/2/14**  
> 上游已更新，接下来不区分网页版和 API 版。  
> 1.6.x 及以上版本将为最新版。

> ~~**2023/2/10**~~  
> ~~本项目分为网页版和API版两种模式。~~  
> ~~网页版代表版本号为 v1.5.x 的版本； API 版代表版本号为 v1.6 的版本~~  
> ~~具体区别见：https://github.com/lss233/chatgpt-mirai-qq-bot/issues/82~~  
> ~~当前浏览的是 API 版，点[这里](https://github.com/lss233/chatgpt-mirai-qq-bot/tree/browser-version)切换至网页版。~~


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
* [x] 支持 ChatGPT Plus
* [x] 预设人格初始化


* [交流群](https://jq.qq.com/?_wv=1027&k=voXtxBSw) 会发布最新的项目动态。  
  加群之前先看[这里](https://github.com/lss233/chatgpt-mirai-qq-bot/issues)的内容能不能解决你的问题。  
  如果不能解决，把遇到的问题、**日志**和配置文件准备好后再提问。  
* [调试群](https://jq.qq.com/?_wv=1027&k=TBX8Saq7) 这个群里有很多 ChatGPT QQ 机器人，不解答技术问题。 

![Preview](.github/preview.png)


## 🔧 使用

如果你在使用的过程中遇到问题，可以看[**搭建常见问题解答 | FAQ**](https://github.com/lss233/chatgpt-mirai-qq-bot/issues/85)。   

<details>
    <summary>Linux: 通过快速部署脚本部署 （新人推荐)</summary>

执行下面这行命令启动自动部署脚本。  
它会为你安装 Docker、 Docker Compose 和编写配置文件。  

```bash
bash -c "$(curl -fsSL https://gist.githubusercontent.com/lss233/6f1af9510f47409e0d05276a3af816df/raw/chatgpt-mirai-installer.sh)"
```

</details>

<details>
    <summary>Linux: 通过 Docker Compose 部署 （自带 Mirai)</summary>

我们使用 `docker-compose.yaml` 整合了 [lss233/mirai-http](https://github.com/lss233/mirai-http-docker) 和本项目来实现快速部署。  
但是在部署过程中仍然需要一些步骤来进行配置。  

您可以尝试使用  [@paradox8599](https://github.com/paradox8599) 提供的简易部署脚本：[paradox8599/mirai-chatgpt-setup](https://github.com/paradox8599/mirai-chatgpt-setup) 进行较快地部署。  

**或者**移步至 [Wiki](https://github.com/lss233/chatgpt-mirai-qq-bot/wiki/%E4%BD%BF%E7%94%A8-Docker-Compose-%E9%83%A8%E7%BD%B2%EF%BC%88Mirai---%E6%9C%AC%E9%A1%B9%E7%9B%AE%EF%BC%89) 浏览手工配置的方案。

</details>

<details>
    <summary>Linux: 通过 Docker 部署 （适合已经有 Mirai 的用户)</summary>

1. 找个合适的位置，写你的 `config.cfg`。

2.  执行以下命令，启动 bot：
```bash
# 修改 /path/to/config.cfg 为你 config.cfg 的位置
# XPRA_PASSWORD=123456 中的 123456 是你的 Xpra 密码，建议修改
docker run --name mirai-chatgpt-bot \
    -e XPRA_PASSWORD=123456 \ 
    -v /path/to/config.cfg:/app/config.cfg \
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

参考 `config.example.cfg` 调整配置文件。将其复制为 `config.cfg`，然后修改 `config.cfg`。

配置文件主要包含 mirai-http-api 的连接信息和 OpenAI 的登录信息。

OpenAI 注册教程： https://www.cnblogs.com/mrjade/p/16968591.html  

OpenAI 配置的信息可参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup)。


```properties
[mirai]
# Mirai 相关设置

qq = 请填写机器人的 QQ 号

# 以下设置如果不懂 无需理会

api_key = "1234567890" # mirai-http-api 中的 verifyKey
http_url = "http://localhost:8080" # mirai-http-api 中的 http 回调地址
ws_url = "http://localhost:8080"# mirai-http-api 中的 ws 回调地址

[openai]
# OpenAI 相关设置

# 你的 OpenAI 邮箱
email = "xxxx" 
# 你的 OpenAI 密码
password = "xxx"

# 对于通过 Google 登录或者微软登录的同学，可以使用 session_token 登录
# 此时 email 和 password 可以直接删除
# session_token = "一串 ey 开头的东西"

# 机器人情感值，范围  0 ~ 1，越高话越多
temperature = 0.5

# 如果你的网络不好，可以设置一个本地代理
# proxy="http://127.0.0.1:1080"

# 如果你 OpenAI 禁止你所在的地区使用，可以使用第三方服务代理验证
# 警告：设置为 true 以后，你的 OpenAI 账户信息会发送至第三方
insecure_auth = false

# 使用付费模型（plus 用户使用）
paid = false

[text_to_image]
# 文字转图片
font_size = 30 # 字体大小
width = 700  # 图片宽度
font_path = "fonts/sarasa-mono-sc-regular.ttf"  # 字体
offset_x = 50  # 起始点 X
offset_y = 50 # 起始点 Y

[trigger]
# 配置机器人要如何响应，下面所有项均可选 (也就是可以直接删掉那一行)

# 符合前缀才会响应，可以自己增减
prefix = [ "",]

# 配置群里如何让机器人响应，"at" 表示需要群里 @ 机器人，"mention" 表示 @ 或
require_mention = "at"

# 重置会话的命令
reset_command = [ "重置会话",]

# 回滚会话的命令
rollback_command = [ "回滚会话",]

[response]
# 匹配指令成功但没有对话内容时发送的消息
placeholder = "您好！我是 Assistant，一个由 OpenAI 训练的大型语言模型。我不是真正的人，而是一个计算机程序，可以通过文本聊天来帮助您解决问题。如果您有任何问题，请随时告诉我，我将尽力回答。\n如果您需要重置我们的会话，请回复`重置会话`。"

# 发生错误时要发送的消息
error_format = "出现故障！如果这个问题持续出现，请和我说“重置会话” 来开启一段新的会话，或者发送 “回滚对话” 来回溯到上一条对话，你上一条说的我就当作没看见。\n{exc}"

# 是否要回复触发指令的消息
quote = true

# 发送下面那个提醒之前的等待时间
timeout = 30.0

# 超过响应时间时要发送的提醒
timeout_format = "我还在思考中，请再等一下~"

# 重置会话时发送的消息
reset = "会话已重置。"

# 回滚成功时发送的消息
rollback_success = "已回滚至上一条对话，你刚刚发的我就忘记啦！"

# 回滚失败时发送的消息
rollback_fail = "回滚失败，没有更早的记录了！"

# 服务器提示 429 错误时的回复
request_too_fast = "当前正在处理的请求太多了，请稍等一会再发吧！"

[system]
# 是否自动同意进群邀请
accept_group_invite = false

# 是否自动同意好友请求
accept_friend_request = false

[presets]
# 切换预设的命令： 加载预设 猫娘
command = "加载预设 (\\w+)"

loaded_successful = "预设加载成功！"

[presets.keywords]
# 预设关键词 <-> 实际文件
"正常" = "presets/default.txt"
"猫娘" = "presets/catgirl.txt"

```

### OpenAI 登录

目前我们支持邮箱密码登录和 session_token 登录两种方式。  

#### 邮箱密码登录

你只需要填写 OpenAI 的邮箱和密码即可。  

```properties
# 前面别的东西
[openai]
# 你的 OpenAI 邮箱
email = "xxxx" 
# 你的 OpenAI 密码
password = "xxx"
# 后面别的东西
```

**登录不了？**

如果你所在的地区无法使用 OpenAI，可以尝试开启 `insecure_auth` 配置项。  

开启后，你的账户密码将发送至一个第三方的代理服务器进行验证。  

```properties
# 前面别的东西
[openai]
# 你的 OpenAI 邮箱
email = "xxxx" 
# 你的 OpenAI 密码
password = "xxx"

# 通过第三方代理服务器验证
insecure_auth = true
```

### session_token 验证

对于通过 Google 登录或者微软登录的同学，可以使用 session_token 方式进行登录。  

使用这种方式登录时不需要填写邮箱和密码。  

需要注意的是，session_token 过期比较频繁，过期后需要重新设置。  

session_token 的获取方式可参考：[请问怎么获取 session_token](https://github.com/lss233/chatgpt-mirai-qq-bot/issues/96)  

```properties
# 前面别的东西
[openai]

session_token = "一串 ey 开头的东西"
```

### 使用正向代理

如果你的网络访问 OpenAI 比较慢，或者你的 IP 被封锁了，或者出现了 Unknown error 的情况，可以通过配置代理的方式来连接到 OpenAI。  

支持使用正向代理方式访问 OpenAI，你需要一个 HTTTP/HTTPS 代理服务器：

```properties
[openai]
# 前面别的东西

# 请注意，由于现在 OpenAI 封锁严格，你需要一个
# 尽量使用独立的代理服务器，不要使用和其他人共用 IP 的代理
# 否则会出现无限弹出浏览器的问题  

proxy="http://127.0.0.1:1080"

# 后面别的东西
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

## Star History

如果你觉得本项目对你有帮助的话，欢迎点一个 Star!  

[![Star History Chart](https://api.star-history.com/svg?repos=lss233/chatgpt-mirai-qq-bot&type=Timeline)](https://star-history.com/#lss233/chatgpt-mirai-qq-bot&Timeline)
