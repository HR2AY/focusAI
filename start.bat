@echo off
cd /d "%~dp0"
chcp 65001 >nul
title FocusEngine

echo ==========================================
echo   FocusEngine Launcher (Agent-Ready)
echo ==========================================
echo.

:: --- Step 1: Detect Python ---
echo [1/3] Checking Python...
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 ( set PY=py & goto venv )
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 ( set PY=python & goto venv )

echo.
echo [ERROR] Python not found.
echo Please install Python 3.8+ from https://python.org
echo and check "Add python.exe to PATH" during setup.
pause
exit /b 1

:: --- Step 2: Virtual environment ---
:venv
echo [2/3] Preparing virtual environment...
if not exist "venv\Scripts\python.exe" (
    %PY% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create venv. Check your Python installation.
        pause
        exit /b 1
    )
)

:: --- Step 3: Install / update dependencies ---
:deps
echo [3/3] Installing dependencies...
"venv\Scripts\python.exe" -m pip install -q --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple openai pillow pywebview
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Mirror failed, retrying with official PyPI...
    "venv\Scripts\python.exe" -m pip install -q --upgrade openai pillow pywebview
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

:: --- Launch ---
:start
echo.
echo [OK] Starting FocusEngine (API port: 8765)...
echo      You can minimize this window, but do NOT close it.
echo.
"venv\Scripts\python.exe" main.py %*

echo.
echo FocusEngine exited.
pause
