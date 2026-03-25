@echo off
:: 设置控制台为 UTF-8 编码
chcp 65001 >nul
title FocusEngine 引擎启动器

echo ==========================================
echo      FocusEngine 启动程序 (Agent-Ready)
echo ==========================================
echo.

:: 1. 检查 Python 环境 (使用 py 启动器避开 Windows Store 假 Python)
echo [INFO] 正在检查 Python 环境...
py --version
if %ERRORLEVEL% NEQ 0 goto NO_PYTHON
goto CHECK_VENV

:NO_PYTHON
echo.
echo [错误] 未检测到有效的 Python 环境！
echo 请前往 python.org 安装 Python 3.8+，并在安装时务必勾选 "Add python.exe to PATH"。
pause
exit /b

:CHECK_VENV
:: 2. 检查虚拟环境
echo [INFO] 检测到 Python，准备检查虚拟环境...
if exist "venv\Scripts\python.exe" goto INSTALL_DEPS
echo [INFO] 首次运行，正在创建独立的虚拟环境 (venv)...
py -m venv venv

:INSTALL_DEPS
:: 3. 直接使用虚拟环境的 pip 安装依赖 (绝对路径调用，最稳妥)
echo [INFO] 正在检查并安装核心运行库...
"venv\Scripts\python.exe" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openai pillow pywebview

:START_APP
:: 4. 启动程序
echo.
echo [INFO] 环境准备就绪！
echo [INFO] 正在启动 FocusEngine 引擎与本地 API 服务 (端口: 8765)...
echo [INFO] 提示：你可以最小化此控制台窗口，但请勿关闭。
echo.

"venv\Scripts\python.exe" main.py

echo.
echo [INFO] FocusEngine 已退出。
pause
