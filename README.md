# ChatGPT Mirai QQ Bot
This project uses [Ariadne](https://github.com/GraiaProject/Ariadne) and mirai-http-api to provide a ChatGPT chatbot.   

Reverse Engineered ChatGPT by OpenAI [here](https://github.com/acheong08/ChatGPT).  

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
You may refer [here](https://github.com/acheong08/ChatGPT/tree/4a62fee7797962277b6d137b1a7ef98d9960bbb6#development) to setup OpenAI credentials.


4. Start the bot.
```
python3 bot.py
```

5. Happy chating.

