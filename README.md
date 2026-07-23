# Siemens NX Advanced Gesture Controller

Welcome to the **NX Advanced Gesture Controller**! This plugin transforms your standard webcam into a highly responsive, zero-touch 3D navigation tool for Siemens NX. By leveraging MediaPipe's AI hand-tracking and advanced vector mathematics, you can intuitively Rotate, Pan, Zoom, and Roll your 3D models with simple hand gestures.

## 🌟 Key Features

*   **Always-On-Top Mini Window**: The webcam feed acts as a small, unobtrusive picture-in-picture overlay. It stays on top of Siemens NX so you never lose track of your gesture state, without sacrificing your CAD workspace.
*   **Dynamic EMA Tracking Algorithm**: Experience pixel-perfect control. When you move your hand quickly, the algorithm switches to zero-latency tracking for broad movements. As you slow down, it dynamically applies heavy Exponential Moving Average (EMA) smoothing to eliminate micro-tremors.
*   **6-DoF Inspired Navigation**: Complete control including X/Y rotation, Z-axis roll, 2D panning, and depth-based zooming.
*   **Zero Admin Setup**: Designed specifically for strict corporate environments, the installation runs entirely in "user space" and does not require Administrator privileges.

---

## 🛠 Step-by-Step Installation

Because corporate office environments often restrict admin access and internet connectivity, this tool includes robust setup scripts to get you running regardless of your network constraints.

### Method 1: Standard Installation (If you have Internet Access)

Use this method if your computer is connected to the internet and allows Python to download packages.

1.  **Extract the Files**: Place the `nx-gesture-interface` folder anywhere on your computer (e.g., your Documents folder).
2.  **Open the Plugin Folder**: Navigate inside the `nx-plugin` directory.
3.  **Run the Installer**:
    *   On Windows: Double-click `run_server.bat`
    *   On Mac/Linux: Run `bash run_server.sh`
4.  **Wait for Setup**: The script will automatically create an isolated Python virtual environment (`.venv`) and install the required AI libraries (OpenCV, MediaPipe, NumPy).
5.  **Done!** The server will launch immediately after installation. In the future, running this script will skip the installation and just start the server.

### Method 2: Offline USB Installation (Strict Office Firewalls)

Use this method if your office computer blocks `pip` from downloading files from the internet.

**Part A: On your Personal Computer (At Home / Unrestricted Network)**
1.  Navigate to the `nx-plugin` folder on your personal machine.
2.  Run the offline downloader script:
    *   On a Mac: `bash download_windows_wheels.sh`
    *   On Windows: Double-click `download_windows_wheels.bat`
3.  This script will download exactly what your office computer needs into a new folder called `nx-packages`.
4.  Copy the entire `nx-gesture-interface` folder (which now contains `nx-packages`) to a USB thumb drive.

**Part B: On your Office Computer (No Internet)**
1.  Copy the folder from your USB drive to your office computer.
2.  Navigate to the `nx-plugin` folder and double-click `run_server.bat`.
3.  The script will detect the `nx-packages` folder and perform a completely offline installation automatically!

---

## 🎮 How to Use in Siemens NX

Once the installation is complete, follow these exact steps every time you want to use the gesture controller.

### Step 1: Start the Gesture Engine
Double-click `run_server.bat` (or `.sh`). You will see a small overlay window appear showing your webcam feed. As long as this window is open, the system is tracking your hands.

### Step 2: Connect Siemens NX
1. Open Siemens NX and load any 3D model or assembly.
2. Go to the top menu and select **File > Execute > NX/Open** (Shortcut: `Ctrl+U`).
3. Browse to the `nx-plugin` folder and select the `nx_view_controller.py` script.
4. *Look at the bottom status bar in NX—it should read: "NX Gesture Control Active".*

### Step 3: Master the Gestures

Bring your hand into the camera's view to take control. The system tracks your **Index Finger Knuckle** as the primary anchor point.

| Gesture Command | Hand Shape | Movement Action | Result in Siemens NX |
| :--- | :--- | :--- | :--- |
| **ROTATE (X/Y)** | ✊ **Fist** (All fingers closed) | Move hand Up/Down/Left/Right | Orbits the camera around the model. |
| **ROLL (Z)** | ✊ **Fist** (All fingers closed) | Twist your wrist clockwise or counter-clockwise | Rolls the camera along the Z-axis. |
| **PAN** | ✋ **Flat Open Hand** (Fingers spread) | Move hand Up/Down/Left/Right | Slides the model across the screen. |
| **ZOOM** | 🤏 **Pinch** (Thumb and Index touching) | Move hand vertically Up/Down | Zooms in (up) and out (down). |
| **FIT VIEW** | 👌 **"OK" Sign** (Thumb & Index pinched, other 3 open) | Hold the pose for 1 second | Instantly centers and fits the entire model to the screen. |

---

## ⚙️ Troubleshooting & Tuning

**The camera window is open, but NX isn't responding.**
*   Ensure that you executed `nx_view_controller.py` *after* starting the server.
*   Make sure you have an active 3D part open in the NX workspace.

**The movements are too fast/too slow.**
*   You can tune the sensitivities by opening `nx_view_controller.py` in Notepad.
*   Look for `ROT_SENSITIVITY`, `PAN_SENSITIVITY`, `ZOOM_SENSITIVITY`, and `ROLL_SENSITIVITY` near the top of the file and adjust the numbers to your liking.

**The camera view is jerky.**
*   Ensure your room is well-lit. MediaPipe tracking degrades in low light.
*   The system uses a `DEADZONE` parameter inside `gesture_server.py`. If your hand shakes naturally, you can increase `DEADZONE = 0.002` to `0.005` to ignore larger micro-tremors.
