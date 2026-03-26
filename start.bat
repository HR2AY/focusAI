@echo off
:: 切换到脚本所在目录，确保相对路径正确（双击运行时必须）
cd /d "%~dp0"
chcp 65001 >nul
title FocusEngine 引擎启动器

echo ==========================================
echo      FocusEngine 启动程序 (Agent-Ready)
echo ==========================================
echo.

:: -----------------------------------------------
:: 1. 检测 Python（优先 py 启动器，fallback python）
:: -----------------------------------------------
echo [INFO] 正在检查 Python 环境...
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON=py
    goto CHECK_VENV
)
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON=python
    goto CHECK_VENV
)

echo.
echo [错误] 未检测到 Python！
echo 请前往 https://python.org 安装 Python 3.8+，安装时勾选 "Add python.exe to PATH"。
pause
exit /b 1

:: -----------------------------------------------
:: 2. 创建 / 复用虚拟环境
:: -----------------------------------------------
:CHECK_VENV
if exist "venv\Scripts\python.exe" goto INSTALL_DEPS
echo [INFO] 首次运行，正在创建虚拟环境...
%PYTHON% -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 虚拟环境创建失败，请确认 Python 安装完整。
    pause
    exit /b 1
)

:: -----------------------------------------------
:: 3. 安装 / 更新依赖
:: -----------------------------------------------
:INSTALL_DEPS
echo [INFO] 正在检查并安装核心运行库...
"venv\Scripts\python.exe" -m pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple openai pillow pywebview
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [警告] 依赖安装遇到问题，尝试不使用镜像源重试...
    "venv\Scripts\python.exe" -m pip install -q openai pillow pywebview
)

:: -----------------------------------------------
:: 4. 启动
:: -----------------------------------------------
:START_APP
echo.
echo [INFO] 环境准备就绪！
echo [INFO] 正在启动 FocusEngine 引擎与本地 API 服务 (端口: 8765)...
echo [INFO] 提示：可最小化此控制台，但请勿关闭。
echo.

"venv\Scripts\python.exe" main.py

echo.
echo [INFO] FocusEngine 已退出。
pause
