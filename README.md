# ChatGPT Mirai QQ Bot
This project uses [Ariadne](https://github.com/GraiaProject/Ariadne) and mirai-http-api to provide a ChatGPT chatbot.   

Reverse Engineered ChatGPT by OpenAI [here](https://github.com/acheong08/ChatGPT).  

## 基于
 - [Ariadne](https://github.com/GraiaProject/Ariadne)
 - [mirai-http-api](https://github.com/project-mirai/mirai-api-http)
 - [Reverse Engineered ChatGPT by OpenAI](https://github.com/acheong08/ChatGPT).  
 - 
![Preview](.github/preview.png)

## Setup  
1. Make sure you have [Mirai](https://github.com/mamoe/mirai) and Python version >= 3.9.0 installed. 

2. Clone this project and installing dependencies:
```bash
git clone https://github.com/lss233/chatgpt-mirai-qq-bot
cd chatgpt-mirai-qq-bot
pip3 install -r requirements.txt
```

3. Rename `config.example.json` to `config.json`, and replace it by your own values.  
You may refer [here](https://github.com/acheong08/ChatGPT/wiki/Setup) to setup OpenAI credentials.


4. Start the bot.
```
python3 bot.py
```

5. Happy chating.

## 使用
1. 部署mirai，安装mirai-http-api 插件

2. 下载本项目:
```bash
git clone https://github.com/lss233/chatgpt-mirai-qq-bot
cd chatgpt-mirai-qq-bot
pip3 install -r requirements.txt
```

3. 配置
   重命名 `config.example.json` 为 `config.json`, 更改里面的配置.  
   token获取教程 [here](https://github.com/acheong08/ChatGPT/wiki/Setup) to setup OpenAI credentials.
   
4. 启动 bot.
```
python3 bot.py
```

5. Happy chating.   
