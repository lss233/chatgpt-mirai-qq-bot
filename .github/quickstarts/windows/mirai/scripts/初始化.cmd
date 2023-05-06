@ECHO OFF
@CHCP 65001
SET BASE_DIR=%cd%

ECHO 正在初始化 Mirai...
ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ECHO !!
ECHO !! 如果您是新手，没有特殊需求。一路回车即可安装      !!!!
ECHO !! 如果您在执行的过程出现错误，可以重新启动此脚本    !!!!
ECHO !! 如果您遇到问题，可以提交 issue，或者在交流群询问  !!!!
ECHO !!
ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ECHO 当前的安装路径为 %BASE_DIR%
ECHO 提示：请注意安装路径中不要有空格，否则可能会导致安装失败
ECHO 提示：安装前先解压程序，不要在压缩包中直接运行
pause

cd "%BASE_DIR%\mirai"
@REM mcl-installer.exe

@REM ECHO 安装 mirai-api-http 插件...
@REM ECHO 插件介绍：https://github.com/project-mirai/mirai-api-http
@REM cmd /c mcl.cmd --update-package net.mamoe:mirai-api-http --channel stable-v2 --type plugin
@REM
@REM ECHO 安装 mirai-device-generator 插件...
@REM ECHO 插件介绍：https://github.com/cssxsh/mirai-device-generator
@REM cmd /c mcl.cmd --update-package xyz.cssxsh.mirai:mirai-device-generator --channel stable --type plugin
@REM
@REM ECHO 安装 fix-protocol-version 插件...
@REM ECHO 插件介绍：https://github.com/cssxsh/fix-protocol-version
@REM cmd /c mcl.cmd --update-package xyz.cssxsh.mirai:fix-protocol-version --channel stable --type plugin

cd "%BASE_DIR%"
ECHO 复制 mirai-http-api 配置信息...
mkdir "%BASE_DIR%\mirai\config\net.mamoe.mirai-api-http"
copy "%BASE_DIR%\files\mirai-http-api-settings.yml" "%BASE_DIR%\mirai\config\net.mamoe.mirai-api-http\setting.yml"

ECHO Mirai 初始化完毕。
cd "%BASE_DIR%\chatgpt"

ECHO 接下来开始初始化 ChatGPT
ECHO 初始化 pip...
set PYTHON_EXECUTABLE="%BASE_DIR%\python3.11\python.exe"
cd "%BASE_DIR%\python3.11"
@REM %PYTHON_EXECUTABLE% get-pip.py

ECHO 安装依赖...
cd "%BASE_DIR%\chatgpt"

REM 如果下载的依赖不是最新版
REM 请修改 https://mirrors.aliyun.com/pypi/simple/ 为 https://pypi.org/simple/
REM 然后重新执行

%PYTHON_EXECUTABLE% -m pip install -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ -r requirements.txt

ECHO 接下来将会打开 config.cfg，请修改里面的信息。

cd "%BASE_DIR%\chatgpt"
COPY config.example.cfg config.cfg
notepad config.cfg
cd "%BASE_DIR%"

cls

COPY "%BASE_DIR%\files\mirai\scripts\启动ChatGPT.cmd" .
COPY "%BASE_DIR%\files\mirai\scripts\启动Mirai.cmd" .
ECHO "接下来请先执行 【启动ChatGPT.cmd】，启动程序。"
ECHO "然后执行 【启动Mirai.cmd】 并登录机器人 QQ，然后就可以开始使用了！"

pause
