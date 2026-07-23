#!/bin/bash
echo "Downloading Windows dependencies (Python 3.10) for offline installation..."
mkdir -p nx-packages
python3 -m pip download -d ./nx-packages --platform win_amd64 --python-version 310 --only-binary=:all: opencv-python mediapipe numpy
echo "Done! The nx-packages folder is ready to be transferred to your Windows machine."
