@echo off

cd /d "%~dp0"

call .venv\Scripts\activate.bat

python app\run_All.py

pause