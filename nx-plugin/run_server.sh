#!/bin/bash
echo "Starting NX Advanced Gesture Server..."
cd "$(dirname "$0")"

# Activate the virtual environment
source .venv/bin/activate

# Run the python server
python3 gesture_server.py
