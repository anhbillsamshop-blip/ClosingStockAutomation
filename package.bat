@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

echo [1/4] Installing Python build dependencies...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :error
"%PYTHON%" -m pip install "pyinstaller>=6.0"
if errorlevel 1 goto :error

echo [2/4] Building React frontend...
pushd ClosingStockAutomation_UI\dataflow
call npm ci
if errorlevel 1 (
    popd
    goto :error
)
call npm run build
if errorlevel 1 (
    popd
    goto :error
)
popd

echo [3/4] Building standalone executable...
if exist release rmdir /s /q release
if exist build\pyinstaller rmdir /s /q build\pyinstaller
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --console ^
    --name ClosingStockAutomation ^
    --distpath release ^
    --workpath build\pyinstaller ^
    --specpath build ^
    --paths . ^
    --paths ClosingStockAutomation_UI ^
    --add-data "%~dp0ClosingStockAutomation_UI\dataflow\dist;ClosingStockAutomation_UI\dataflow\dist" ^
    --collect-all duckdb ^
    --hidden-import app.converter_core ^
    --hidden-import app.output_delivery ^
    --hidden-import app.run_All ^
    ClosingStockAutomation_UI\server.py
if errorlevel 1 goto :error

echo [4/4] Writing release instructions...
>release\README.txt echo Closing Stock Automation
>>release\README.txt echo.
>>release\README.txt echo Chay ClosingStockAutomation.exe de mo giao dien.
>>release\README.txt echo May nay khong can cai Node.js, Python hoac package nao.
>>release\README.txt echo Chon cac thu muc CSV va output trong giao dien.
echo.
echo DONE: release\ClosingStockAutomation.exe
exit /b 0

:error
echo.
echo PACKAGE FAILED. Xem loi phia tren.
exit /b 1