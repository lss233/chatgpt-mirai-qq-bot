@ECHO OFF
@CHCP 65001

TITLE [ChatGPT for QQ] go-cqhttp 端正在运行...

SET PATH="%cd%\ffmpeg\bin;%PATH%"

cd go-cqhttp && go-cqhttp -faststart
TITLE [ChatGPT for QQ] go-cqhttp 端已停止运行

echo 程序已停止运行
PAUSE