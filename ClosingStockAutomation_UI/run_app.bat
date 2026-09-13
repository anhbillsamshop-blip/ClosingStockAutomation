@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "APP_DIR=%~dp0"
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    set "PYTHON=python"
)

cd /d "%APP_DIR%"

echo ========================================
echo   CLOSING STOCK AUTOMATION
echo ========================================
echo.
echo Python: %PYTHON%
echo.
echo Dang khoi dong server...
echo.

"%PYTHON%" "%APP_DIR%\server.py"

pause