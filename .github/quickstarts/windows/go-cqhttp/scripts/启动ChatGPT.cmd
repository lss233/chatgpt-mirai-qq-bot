@ECHO OFF
@CHCP 65001

SET PATH="%cd%\ffmpeg\bin;%PATH%"

TITLE [ChatGPT for QQ] ChatGPT 端正在运行...
cd chatgpt && ..\python3.11\python.exe bot.py
TITLE [ChatGPT for QQ] ChatGPT 端已停止运行
ECHO 程序已停止运行。
PAUSE