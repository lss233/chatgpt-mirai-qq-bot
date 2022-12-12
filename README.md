# ChatGPT Mirai QQ Bot

一款使用 OpenAI 的 ChatGPT 进行聊天的 QQ 机器人！  

基于
 - [Ariadne](https://github.com/GraiaProject/Ariadne)
 - [mirai-http-api](https://github.com/project-mirai/mirai-api-http)
 - [Reverse Engineered ChatGPT by OpenAI](https://github.com/acheong08/ChatGPT).  

支持：  
* [x] 文字转图片发送  
* [x] 群聊回复引用
* [ ] 关键词触发回复
* [x] 反向代理/正向代理
* [x] 多种方式登录 OpenAI


[交流群](https://jq.qq.com/?_wv=1027&k=3X55LqoY)  

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
docker run --name mirai-chatgpt-bot \
    -v /path/to/config.json:/app/config.json \
    --network host \
    lss233/chatgpt-mirai-qq-bot:latest
```
</details>

<details>
    <summary>Windows: 快速部署包 (自带 Mirai，新人推荐）</summary>

我们为 Windows 用户制作了一个快速启动包，可以在 [Release](https://github.com/lss233/chatgpt-mirai-qq-bot/releases) 中找到。    

文件名为：`quickstart-windows-amd64.zip`  
</details>

<details>
    <summary>手动部署</summary>

提示：你需要 Python >= 3.9 才能运行本项目  

1. 部署 Mirai ，安装 mirai-http-api 插件

2. 下载本项目:
```bash
git clone https://github.com/lss233/chatgpt-mirai-qq-bot
cd chatgpt-mirai-qq-bot
pip3 install -r requirements.txt
```

3. 重命名 `config.example.json` 为 `config.json`, 更改里面的配置.  


4. 启动 bot.
```bash
python3 bot.py
```
</details>


## ⚙ 配置文件

你可以参考 `config.example.json` 来写配置文件。   

配置文件主要包含 mirai-http-api 的连接信息和 OpenAI 的登录信息。

OpenAI 注册教程： https://www.cnblogs.com/mrjade/p/16968591.html  

OpenAI 配置的信息可参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup).  

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
    }
}
```

### 🚀 使用代理

如果你的网络访问 OpenAI 比较慢，或者你的 IP 被封锁了（需要验证码）， 可以通过配置代理的方式来连接到 OpenAI。  

代理有两种方式，分别为 反向代理 和 正向代理，你只需要配置其中一种方式即可。 

#### 反向代理  

使用反向代理方式访问 OpenAI, 你需要准备一个可以访问到 `chat.openai.com` 的代理网站。  

这可以通过 cf worker / nginx 反向代理 / vercel 等来实现，在此不作赘述。

> 可以参考： https://www.j000e.com/cloudflare/cfworkers_reverse_proxy.html  
>
>   你只需要代理 `chat.openai.com` 这一个域名即可。
  
在 `"openai"` 中加入一条 `"base_url": <你的反代URL>` 即可。  

举个例子：
```jsonc
    // 前面别的东西
    "openai": {
        "session_token": "SESSION_TOKEN", // 你的 OpenAI 的 session_token，详见下
        "base_url": "https://chatgpt.proxy.lss233.com/"
    },
    // 后面别的东西
```

之后，所有发往 `chat.openai.com` 的请求都会通过 `base_url` 中配置的地址发送。  

#### 正向代理  

使用正向代理方式访问 OpenAI, 你需要在运行本项目的主机上有一个可以访问的 HTTTP/HTTPS 代理服务器。  

  
在 `"openai"` 中加入一条 `"proxy": <你的代理服务器地址>` 即可。  

举个例子：
```jsonc
    // 前面别的东西
    "openai": {
        "session_token": "SESSION_TOKEN", // 你的 OpenAI 的 session_token，详见下
        "proxy": "http://localhost:1080"
    },
    // 后面别的东西
```

### OpenAI 登录不了

> 由于 OpenAI 官网的修改，目前仅支持 `session_token` 登录。  

`Captcha detect`、 `State not found` 等各种问题，都可以通过配置 `session_token` 登录。

举个例子：
```jsonc
    // 前面别的东西
    "openai": {
        "session_token": "一串ey开头的很长的东西...", // 注意， ey 开头的可能有两个，别复制错了！
        "proxy": "http://localhost:1080"
    },
    // 后面别的东西
```

请参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup) 了解 `session_token` 的获取方法。

如果你看见 `Exception: Wrong response code` 的错误，说明你的 `session_token` 过期了，或者不正确。  

注： `session_token` 具有时效性，如果长期出现错误的情况，请重新获取你的  `session_token`。 [#29](https://github.com/lss233/chatgpt-mirai-qq-bot/issues/29)



## 📷 图片转文字

本项目会在向 QQ 群发送消息失败时，自动将消息转为图片发送。  

字体文件存放于 `fonts/` 目录中。  

默认使用的字体是 [更纱黑体](https://github.com/be5invis/Sarasa-Gothic)。  
