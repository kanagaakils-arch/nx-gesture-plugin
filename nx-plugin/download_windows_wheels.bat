@echo off
echo Downloading Windows dependencies (Python 3.10) for offline installation...
if not exist "nx-packages" mkdir nx-packages
pip download -d .\nx-packages opencv-python mediapipe numpy
echo.
echo Done! The nx-packages folder is ready.
pause
