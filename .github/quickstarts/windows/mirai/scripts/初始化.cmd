@ECHO OFF
@CHCP 65001
SET BASE_DIR=%cd%

ECHO ���ڳ�ʼ�� Mirai...
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

cd "%BASE_DIR%\mirai"
@REM mcl-installer.exe

@REM ECHO ��װ mirai-api-http ���...
@REM ECHO ������ܣ�https://github.com/project-mirai/mirai-api-http
@REM cmd /c mcl.cmd --update-package net.mamoe:mirai-api-http --channel stable-v2 --type plugin
@REM
@REM ECHO ��װ mirai-device-generator ���...
@REM ECHO ������ܣ�https://github.com/cssxsh/mirai-device-generator
@REM cmd /c mcl.cmd --update-package xyz.cssxsh.mirai:mirai-device-generator --channel stable --type plugin
@REM
@REM ECHO ��װ fix-protocol-version ���...
@REM ECHO ������ܣ�https://github.com/cssxsh/fix-protocol-version
@REM cmd /c mcl.cmd --update-package xyz.cssxsh.mirai:fix-protocol-version --channel stable --type plugin

cd "%BASE_DIR%"
ECHO ���� mirai-http-api ������Ϣ...
mkdir "%BASE_DIR%\mirai\config\net.mamoe.mirai-api-http"
copy "%BASE_DIR%\files\mirai-http-api-settings.yml" "%BASE_DIR%\mirai\config\net.mamoe.mirai-api-http\setting.yml"

ECHO Mirai ��ʼ����ϡ�
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
COPY config.example.cfg config.cfg
notepad config.cfg
cd "%BASE_DIR%"

cls

COPY "%BASE_DIR%\files\scripts\����ChatGPT.cmd" .
COPY "%BASE_DIR%\files\scripts\����Mirai.cmd" .
ECHO "����������ִ�� ������ChatGPT.cmd������������"
ECHO "Ȼ��ִ�� ������Mirai.cmd�� ����¼������ QQ��Ȼ��Ϳ��Կ�ʼʹ���ˣ�"

pause
