@echo off
setlocal

REM Move to this script's directory
cd /d "%~dp0"

REM Prefer py launcher on Windows, fallback to python
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
) else (
    python app.py
)

endlocal
