@echo off
cd /d "%~dp0"
echo ---------------------------------------------------
echo    STARTING GBC RESOLUTIONS APP (High Performance)
echo ---------------------------------------------------
echo.

:: 1. Activate the virtual environment
call venv\Scripts\activate

:: 2. Run Granian with 4 workers
granian --interface asgi app:app --workers 4 --port 8000

pause