@echo off
title MT5 Distributed Worker Manager
echo ========================================================
echo  MT5 Distributed Worker Manager Node
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo [.env not found. Copying .env.example...]
    copy .env.example .env
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.9+ (64-bit) and add to PATH.
    pause
    exit /b 1
)

echo Starting Worker Manager...
python worker_manager.py
pause
