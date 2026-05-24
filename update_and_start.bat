@echo off
setlocal

REM Move to this script's directory
cd /d "%~dp0"

echo [1/2] Updating repository...
git pull
if errorlevel 1 (
    echo.
    echo Git pull failed. Please check the error above.
    pause
    exit /b 1
)

echo [2/2] Starting app.py...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
) else (
    python app.py
)

endlocal
