@REM ...

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

ECHO 提示：现在请按【回车键】继续操作

pause

cd "%BASE_DIR%\kirara_ai"

ECHO 接下来开始初始化

ECHO 初始化 pip...

set PYTHON_EXECUTABLE="%BASE_DIR%\python3.11\python.exe"

cd "%BASE_DIR%\python3.11"

@REM %PYTHON_EXECUTABLE% get-pip.py

ECHO 安装依赖...

cd "%BASE_DIR%\kirara_ai"

REM 如果下载的依赖不是最新版

REM 请修改 https://mirrors.aliyun.com/pypi/simple/ 为 https://pypi.org/simple/

REM 然后重新执行

%PYTHON_EXECUTABLE% -m pip install -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ -r requirements.txt

cd "%BASE_DIR%"

cls

COPY "%BASE_DIR%\files\scripts\启动.cmd" .

ECHO 安装完毕。

ECHO 接下来请执行 启动.cmd 启动程序。

ECHO 如果需要重新安装，请重新运行此脚本，但愿不用。

pause
