@REM ...

@ECHO OFF

@CHCP 65001

TITLE [Kirara AI] AI 系统正在运行...

SET PATH=%cd%\python3.11;%cd%\ffmpeg\bin;%PATH%

python -m kirara_ai

TITLE [Kirara AI] AI 系统已停止运行

ECHO 程序已停止运行。

PAUSE