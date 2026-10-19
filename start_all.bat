@echo off
title MT5 Distributed Terminal System
echo ======================================================================
echo    MT5 Distributed Terminal Hub and Worker Manager
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Central Controller Hub on port 8000...
start "MT5 Central Hub" cmd /k "cd backend && python run_server.py"

echo Waiting 5 seconds for Central Hub to be ready...
timeout /t 5 /nobreak >nul

echo [2/3] Starting Frontend Dashboard on port 3000...
start "MT5 Frontend Dashboard" cmd /k "cd frontend && npm run dev"

echo [3/3] Starting Local Worker Manager Node...
start "MT5 Local Worker Manager" cmd /k "cd worker_node && python worker_manager.py"

echo.
echo ======================================================================
echo All MT5 Distributed Cluster services launched!
echo ----------------------------------------------------------------------
echo Web Dashboard (Vite):   http://localhost:3000
echo Central Hub (FastAPI):  http://127.0.0.1:8000
echo Interactive API Docs:   http://127.0.0.1:8000/docs
echo ======================================================================
echo.
pause
