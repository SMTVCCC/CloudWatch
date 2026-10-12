@echo off
REM CloudWatch Windows 启动脚本
cd /d %~dp0

if not exist .venv (
    echo [CloudWatch] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [CloudWatch] Installing dependencies...
pip install -q -r requirements.txt

echo [CloudWatch] Starting on http://0.0.0.0:8000
python main.py
pause
