@echo off
setlocal
cd /d "%~dp0"

set "PYTHONW=..\.venv\Scripts\pythonw.exe"
set "PYTHON=..\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found: %~dp0..\.venv
    echo Create it first:  python -m venv ..\.venv
    echo Then install deps:  ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if exist "%PYTHONW%" (
    start "" "%PYTHONW%" main.py
) else (
    start "" "%PYTHON%" main.py
)
