@ECHO OFF
@CHCP 65001
SET BASE_DIR=%cd%

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

cd "%BASE_DIR%\go-cqhttp"

cd "%BASE_DIR%"
ECHO 复制  配置信息...
set /p "bot_qq=请输入机器人QQ号："
copy "%BASE_DIR%\files\go-cqhttp\config.yml" "%BASE_DIR%\go-cqhttp\"
copy "%BASE_DIR%\files\go-cqhttp\device.json" "%BASE_DIR%\go-cqhttp\"
setlocal enabledelayedexpansion
set "file=%BASE_DIR%\go-cqhttp\config.yml"
set "search=YOUR_BOT_QQ_HERE"
set "replace=!bot_qq!"
if exist "%file%" (
    for /f "usebackq delims=" %%a in ("%file%") do (
        set "line=%%a"
        set "line=!line:%search%=%replace%!"
        echo(!line!
    )
) > "%file%.new"
move /y "%file%.new" "%file%" > nul
ECHO go-cqhttp 初始化完毕。
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
COPY %BASE_DIR%\files\config.example.go-cqhttp.cfg config.cfg
notepad config.cfg
cd "%BASE_DIR%"

cls

COPY "%BASE_DIR%\files\go-cqhttp\scripts\启动ChatGPT.cmd" .
COPY "%BASE_DIR%\files\go-cqhttp\scripts\启动go-cqhttp.cmd" .
ECHO "接下来请先执行 【启动ChatGPT.cmd】，启动程序。"
ECHO "然后执行 【启动go-cqhttp.cmd】 并登录机器人 QQ，然后就可以开始使用了！"

pause
