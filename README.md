# Siemens NX Advanced Gesture Controller

This repository contains an advanced gesture-control interface designed specifically for Siemens NX. It allows you to manipulate 3D models in the NX viewport (Pan, Zoom, and Rotate) entirely through hand gestures captured by your webcam.

## Architecture

The system operates in two parts to prevent UI locking and ensure smooth performance inside Siemens NX:
1. **Gesture Server (`nx-plugin/gesture_server.py`)**: A standalone Python daemon running OpenCV and MediaPipe. It tracks your hands in real-time, calculates 3D vector movements, applies Exponential Moving Average (EMA) smoothing, and broadcasts the data over a local UDP socket.
2. **NX View Controller (`nx-plugin/nx_view_controller.py`)**: An NX Open Python script that runs inside Siemens NX. It listens to the UDP socket and applies the smoothed transformations directly to the active Work View.

---

## 🚀 Setup & Installation (Windows)

Because corporate office environments often restrict admin access and internet connectivity, this tool is designed to run in **User Space** with completely offline installation support.

### Option A: Standard Installation (With Internet)
If your computer has internet access, simply double-click the included launch script:
```cmd
cd nx-plugin
run_server.bat
```
*This will automatically create an isolated Python virtual environment (`.venv`) and safely install all required dependencies (OpenCV, MediaPipe, NumPy) without requiring Administrator privileges.*

### Option B: Offline Installation (No Internet)
If your office firewall blocks Python from downloading packages:
1. On a **personal computer with internet**, navigate to the `nx-plugin` folder and run the download script:
   ```cmd
   download_windows_wheels.bat
   ```
   *(If you are on a Mac, run `./download_windows_wheels.sh` instead).*
2. This will securely download all required Windows dependencies into a folder called `nx-packages`.
3. Copy the entire `nx-gesture-interface` folder to a USB drive and transfer it to your offline office computer.
4. On your office computer, run `run_server.bat`. It will detect the `nx-packages` folder and perform a fully offline installation!

---

## ✋ How to Use

1. **Start the Gesture Engine**:
   - Double-click `run_server.bat` in the `nx-plugin` folder. 
   - A webcam feed will appear showing your real-time hand tracking.
2. **Connect Siemens NX**:
   - Open Siemens NX and load any 3D model.
   - Go to **File > Execute > NX/Open** (or press `Ctrl+U`).
   - Select the `nx_view_controller.py` script from the `nx-plugin` folder.
3. **Control the Model**:
   - **Rotate:** Make a fist and move your hand (rotates around X and Y axes).
   - **Pan:** Open your hand flat and move it side to side or up and down.
   - **Zoom:** Pinch your thumb and index finger together, and move your hand towards or away from the screen.

## Advanced Features
- **EMA Smoothing**: Hand micro-tremors are filtered out using low-pass exponential smoothing, making camera rotations buttery smooth.
- **Dynamic Deadzones**: Tiny twitches are ignored, while large, deliberate movements scale exponentially for fast navigation.
- **3D Depth Estimation**: Zooming relies on calculated Z-depth changes based on the relative size of your hand, ensuring it works consistently regardless of your distance from the webcam.
