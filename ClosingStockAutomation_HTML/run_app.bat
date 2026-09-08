@echo off
setlocal

title Closing Stock Automation

set "PROJECT_ROOT=C:\ClosingStockAutomation"
set "APP_DIR=%PROJECT_ROOT%\ClosingStockAutomation_HTML"
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

echo ========================================
echo    CLOSING STOCK AUTOMATION
echo ========================================
echo.

if not exist "%PYTHON%" (
    echo KHONG TIM THAY PYTHON:
    echo %PYTHON%
    pause
    exit /b 1
)

if not exist "%APP_DIR%\index.html" (
    echo KHONG TIM THAY:
    echo %APP_DIR%\index.html
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%\app\run_all.py" (
    echo KHONG TIM THAY:
    echo %PROJECT_ROOT%\app\run_all.py
    pause
    exit /b 1
)

cd /d "%APP_DIR%"

echo Python:
echo %PYTHON%
echo.
echo Dang khoi dong server...
echo.
echo MO TRINH DUYET:
echo http://127.0.0.1:3010
echo.

"%PYTHON%" "%APP_DIR%\server.py"

echo.
echo Server da dung.
pause
