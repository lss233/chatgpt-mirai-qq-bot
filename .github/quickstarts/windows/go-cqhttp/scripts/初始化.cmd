@ECHO OFF
@CHCP 65001
SET BASE_DIR=%cd%

ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ECHO !!
ECHO !! ����������֣�û����������һ·�س����ɰ�װ      !!!!
ECHO !! �������ִ�еĹ��̳��ִ��󣬿������������˽ű�    !!!!
ECHO !! ������������⣬�����ύ issue�������ڽ���Ⱥѯ��  !!!!
ECHO !!
ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ECHO ��ǰ�İ�װ·��Ϊ %BASE_DIR%
ECHO ��ʾ����ע�ⰲװ·���в�Ҫ�пո񣬷�����ܻᵼ�°�װʧ��
ECHO ��ʾ����װǰ�Ƚ�ѹ���򣬲�Ҫ��ѹ������ֱ������
pause

cd "%BASE_DIR%\go-cqhttp"

cd "%BASE_DIR%"
ECHO ����  ������Ϣ...
set /p "bot_qq=�����������QQ�ţ�"
copy "%BASE_DIR%\files\go-cqhttp\config.yml" "%BASE_DIR%\go-cqhttp\"
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
ECHO go-cqhttp ��ʼ����ϡ�
cd "%BASE_DIR%\chatgpt"

ECHO ��������ʼ��ʼ�� ChatGPT
ECHO ��ʼ�� pip...
set PYTHON_EXECUTABLE="%BASE_DIR%\python3.11\python.exe"
cd "%BASE_DIR%\python3.11"
@REM %PYTHON_EXECUTABLE% get-pip.py

ECHO ��װ����...
cd "%BASE_DIR%\chatgpt"

REM ������ص������������°�
REM ���޸� https://mirrors.aliyun.com/pypi/simple/ Ϊ https://pypi.org/simple/
REM Ȼ������ִ��

%PYTHON_EXECUTABLE% -m pip install -i https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ -r requirements.txt

ECHO ����������� config.cfg�����޸��������Ϣ��

cd "%BASE_DIR%\chatgpt"
COPY %BASE_DIR%\files\config.example.go-cqhttp.cfg config.cfg
notepad config.cfg
cd "%BASE_DIR%"

cls

COPY "%BASE_DIR%\files\scripts\����ChatGPT.cmd" .
COPY "%BASE_DIR%\files\scripts\����go-cqhttp.cmd" .
ECHO "����������ִ�� ������ChatGPT.cmd������������"
ECHO "Ȼ��ִ�� ������go-cqhttp.cmd�� ����¼������ QQ��Ȼ��Ϳ��Կ�ʼʹ���ˣ�"

pause
