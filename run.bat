@echo off
cls
echo ===================================================
echo   MULTI-AGENT ORCHESTRATOR - GOD MODE EDITION
echo ===================================================
echo.
echo [1/3] Checking environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b
)

echo [2/3] Verifying dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install some dependencies.
    echo The application might not run correctly.
) else (
    echo [OK] Dependencies verified.
)

echo.
echo [3/3] Launching Server...
echo.
echo  -------------------------------------------------
echo  OPEN YOUR BROWSER TO: http://localhost:8000
echo  -------------------------------------------------
echo.
echo Press Ctrl+C to stop the server.
echo.

python server.py
pause
