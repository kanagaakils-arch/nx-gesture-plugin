@echo off
echo Starting NX Advanced Gesture Server...
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Setting up virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

python gesture_server.py
pause
