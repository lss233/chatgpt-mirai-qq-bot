# ChatGPT Mirai QQ Bot

基于
 - [Ariadne](https://github.com/GraiaProject/Ariadne)
 - [mirai-http-api](https://github.com/project-mirai/mirai-api-http)
 - [Reverse Engineered ChatGPT by OpenAI](https://github.com/acheong08/ChatGPT).  

![Preview](.github/preview.png)

## 使用

### 通过 Docker 部署

1. 找个合适的位置，写你的 `config.json`。

2.  执行以下命令，启动 bot：
```bash
# 修改 /path/to/config.json 为你 config.json 的位置
docker run --name mirai-chatgpt-bot -v /path/to/config.json:/app/config.json --network host lss233/chatgpt-mirai-qq-bot:latest
```

### 手动部署

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

## 配置文件

你可以参考 `config.example.json` 来写配置文件。   

配置文件主要包含 mirai-http-api 的连接信息和 OpenAI 的登录信息。

OpenAI 配置的信息可参考 [这里](https://github.com/acheong08/ChatGPT/wiki/Setup).  

```json
{
    "mirai": {
        "qq": 123456, // 机器人的 QQ 账号
        "api_key": "<mirai-http-api 中的 verifyKey>",
        "http_url": "http://localhost:8080", // mirai-http-api 中的 http 回调地址
        "ws_url": "http://localhost:8080" // mirai-http-api 中的 ws 回调地址
    },
    "openai": {
        "email": "<YOUR_EMAIL>", // 你的 OpenAI 账号邮箱
        "password": "<YOUR_PASSWORD>" // 你的 OpenAI 账号密码
    }
}
```