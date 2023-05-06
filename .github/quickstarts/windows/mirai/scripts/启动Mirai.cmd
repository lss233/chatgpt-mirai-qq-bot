@ECHO OFF
@CHCP 65001

TITLE [ChatGPT for QQ] Mirai 端正在运行...

setx /M PATH "%cd%\ffmpeg\bin;%PATH%"

cd mirai && mcl
TITLE [ChatGPT for QQ] Mirai 端已停止运行

echo 程序已停止运行
PAUSE