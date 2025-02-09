@ECHO OFF
@CHCP 65001

TITLE [Kirara AI] AI 系统正在运行...

SET PATH="%cd%\ffmpeg\bin;%PATH%"

cd kirara-ai && ..\python3.11\python.exe main.py
TITLE [Kirara AI] AI 系统已停止运行
ECHO 程序已停止运行。
PAUSE