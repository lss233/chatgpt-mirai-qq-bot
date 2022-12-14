@ECHO OFF
@CHCP 65001
ECHO 正在初始化 Mirai...
ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ECHO !!
ECHO !! 如果您是新手，没有特殊需求。一路回车即可安装      !!!!
ECHO !! 如果您在执行的过程出现错误，可以重新启动此脚本    !!!!
ECHO !! 如果您遇到问题，可以提交 issue，或者在交流群询问  !!!!
ECHO !!
ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
pause 

cd mirai
mcl-installer.exe

ECHO 安装 mirai-api-http 插件...
ECHO 插件介绍：https://github.com/project-mirai/mirai-api-http
cmd /c mcl.cmd --update-package net.mamoe:mirai-api-http --channel stable-v2 --type plugin

ECHO 安装 mirai-device-generator 插件...
ECHO 插件介绍：https://github.com/cssxsh/mirai-device-generator
cmd /c mcl.cmd --update-package xyz.cssxsh.mirai:mirai-device-generator --channel stable --type plugin

cd ..
ECHO 复制 mirai-http-api 配置信息...
mkdir config\net.mamoe.mirai-api-http
copy files\mirai-http-api-settings.yml config\net.mamoe.mirai-api-http\setting.yml

ECHO Mirai 初始化完毕。
cd chatgpt

ECHO 接下来开始初始化 ChatGPT
ECHO 初始化 pip...
set PYTHON_EXECUTABLE=%cd%\python3.9\python.exe
cd python3.9
%PYTHON_EXECUTABLE% get-pip.py
cd ..

ECHO 安装依赖...
%PYTHON_EXECUTABLE% -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

ECHO 初始化 playwright
%PYTHON_EXECUTABLE% -m playwright install

ECHO 接下来将会打开 config.json，请修改里面的信息。
COPY config.example.json config.json
notepad config.json

cd ..
COPY files\scripts\启动.cmd .
ECHO 接下来请执行 启动.cmd 开始使用吧！
pause