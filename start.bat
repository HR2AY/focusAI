@echo off
cd /d "%~dp0"
chcp 65001 >nul
title FocusEngine

echo ==========================================
echo      FocusEngine 启动程序 (Agent-Ready)
echo ==========================================
echo.

:: ── 1. 检测 Python ──────────────────────────
echo [1/3] 检测 Python 环境...
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 ( set PY=py & goto :venv )
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 ( set PY=python & goto :venv )

echo [错误] 未找到 Python，请安装 3.8+ 并勾选 "Add to PATH"
pause & exit /b 1

:: ── 2. 虚拟环境 ─────────────────────────────
:venv
echo [2/3] 准备虚拟环境...
if not exist "venv\Scripts\python.exe" (
    %PY% -m venv venv
    if %ERRORLEVEL% NEQ 0 ( echo [错误] venv 创建失败 & pause & exit /b 1 )
)

:: ── 3. 依赖 ─────────────────────────────────
echo [3/3] 安装 / 更新依赖...
"venv\Scripts\python.exe" -m pip install -q --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple openai pillow pywebview
if %ERRORLEVEL% NEQ 0 (
    echo [提示] 镜像源失败，切换官方源重试...
    "venv\Scripts\python.exe" -m pip install -q --upgrade openai pillow pywebview
    if %ERRORLEVEL% NEQ 0 ( echo [错误] 依赖安装失败 & pause & exit /b 1 )
)

:: ── 启动 ────────────────────────────────────
echo.
echo [OK] 正在启动 FocusEngine (API 端口: 8765)...
echo      可最小化此窗口，但请勿关闭。
echo.
"venv\Scripts\python.exe" main.py %*

echo.
echo FocusEngine 已退出。
pause
