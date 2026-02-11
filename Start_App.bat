@echo off
cd /d "%~dp0"
title GBC Resolutions App (Local Server)
color 0A

echo ---------------------------------------------------
echo    STARTING GBC RESOLUTIONS APP (Vercel Mode)
echo ---------------------------------------------------
echo.

:: 1. KILL OLD SERVERS (Fixes "Port 8000 in use" error)
echo [1/3] Cleaning up old processes...
taskkill /IM python.exe /F >nul 2>&1

:: 2. ACTIVATE ENVIRONMENT
echo [2/3] Activating virtual environment...
call venv\Scripts\activate

:: 3. REFRESH DATA (Excel -> JSON)
echo [3/3] Refreshing data...
python convert_data.py

echo.
echo ---------------------------------------------------
echo    APP IS LIVE! OPEN BROWSER TO:
echo    http://127.0.0.1:8000
echo ---------------------------------------------------
echo.

:: 4. START SERVER (With auto-reload for changes)
uvicorn app:app --reload --port 8000

pause