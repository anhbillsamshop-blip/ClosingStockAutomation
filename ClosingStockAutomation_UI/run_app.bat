@echo off
setlocal

set "PROJECT_ROOT=C:\ClosingStockAutomation"
set "APP_DIR=%PROJECT_ROOT%\ClosingStockAutomation_HTML"
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo KHONG TIM THAY PYTHON:
    echo %PYTHON%
    pause
    exit /b 1
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