@echo off

cd /d "%~dp0"

call .venv\Scripts\activate.bat

python app\closing_stock_duckdb_optimized.py

pause