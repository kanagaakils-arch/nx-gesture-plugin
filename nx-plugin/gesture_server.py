import cv2
import mediapipe as mp
import socket
import json
import time
import math
import threading
import sys
import os
import ctypes

# Load Configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
last_config_mtime = 0

def load_config():
    global UDP_IP, UDP_PORT, TARGET_HAND, DEADZONE, last_config_mtime
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        UDP_IP = config["network"]["udp_ip"]
        UDP_PORT = config["network"]["udp_port"]
        TARGET_HAND = config["tracking"]["target_hand"]
        DEADZONE = config["tracking"]["deadzone"]
        last_config_mtime = os.path.getmtime(CONFIG_FILE)
    except Exception as e:
        pass # Keep old settings if read fails

load_config()

print(f"Starting NX Advanced Gesture Server on {UDP_IP}:{UDP_PORT}")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Setup Windows Mouse Control
try:
    user32 = ctypes.windll.user32
    SCREEN_WIDTH = user32.GetSystemMetrics(0)
    SCREEN_HEIGHT = user32.GetSystemMetrics(1)
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    os_windows = True
except AttributeError:
    # Not running on Windows (e.g., dev environment)
    os_windows = False
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

class CameraStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.grabbed, self.frame = self.cap.read()
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            grabbed, frame = self.cap.read()
            if grabbed:
                self.frame = frame
            time.sleep(0.01)

    def read(self):
        return self.grabbed, self.frame

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=2
)

cam = CameraStream()

WINDOW_NAME = 'NX Gesture Overlay'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 320, 240)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

ema_dx, ema_dy, ema_dz, ema_droll = 0.0, 0.0, 0.0, 0.0
prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
event_cooldown = 0
mouse_clicked = False

def get_3d_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def detect_gesture_advanced(hand_landmarks):
    index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    palm_size = get_3d_distance(index_mcp, pinky_mcp)
    
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    
    # Check each finger state explicitly
    idx_up = get_3d_distance(index_tip, wrist) > get_3d_distance(index_mcp, wrist) * 1.2
    mid_up = get_3d_distance(middle_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist) * 1.2
    rng_up = get_3d_distance(ring_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP], wrist) * 1.2
    pnk_up = get_3d_distance(pinky_tip, wrist) > get_3d_distance(pinky_mcp, wrist) * 1.2
    
    thumb_open = get_3d_distance(thumb_tip, pinky_mcp) > palm_size * 1.5
    pinch_dist = get_3d_distance(thumb_tip, index_tip) / palm_size
    
    open_count = sum([idx_up, mid_up, rng_up, pnk_up])
    
    # 1. Macros
    if idx_up and mid_up and not rng_up and not pnk_up and not thumb_open:
        return "MACRO_UNDO" # Peace Sign
    
    if idx_up and pnk_up and thumb_open and not mid_up and not rng_up:
        return "MACRO_SAVE" # Spider-Man Sign
        
    if thumb_open and open_count == 0:
        return "RESET_VIEW" # Thumbs Up
        
    # 2. Laser Pointer (Index finger only)
    if idx_up and not mid_up and not rng_up and not pnk_up:
        # Check if thumb is pinched to index for a click
        if pinch_dist < 0.6:
            return "LASER_CLICK"
        return "LASER_HOVER"
        
    # 3. Standard Navigation
    if pinch_dist < 0.6 and open_count >= 2:
        return "FIT" # OK Sign
        
    if pinch_dist < 0.6:
        return "ZOOM" # Tight Pinch
        
    if open_count <= 1:
        return "ROTATE_OR_ROLL" # Fist
    elif open_count >= 3:
        return "PAN" # Flat Hand
        
    return "IDLE"

def apply_deadzone_and_scale(val):
    if abs(val) < DEADZONE: return 0.0
    sign = 1 if val > 0 else -1
    return sign * (abs(val) ** 1.3)

try:
    while True:
        # Hot-Reload check
        if os.path.getmtime(CONFIG_FILE) > last_config_mtime:
            load_config()
            print("Config hot-reloaded!")

        success, image = cam.read()
        if not success:
            continue

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        gesture = "IDLE"
        raw_dx, raw_dy, raw_dz, raw_droll = 0.0, 0.0, 0.0, 0.0

        if event_cooldown > 0:
            event_cooldown -= 1

        if results.multi_hand_landmarks and results.multi_handedness:
            target_hand_idx = -1
            for idx, handedness in enumerate(results.multi_handedness):
                if handedness.classification[0].label == TARGET_HAND:
                    target_hand_idx = idx
                    break
                    
            if target_hand_idx != -1:
                hand_landmarks = results.multi_hand_landmarks[target_hand_idx]
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                gesture = detect_gesture_advanced(hand_landmarks)
                
                track_point = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                curr_x, curr_y = track_point.x, track_point.y
                
                if prev_x is not None and prev_y is not None:
                    raw_dx = curr_x - prev_x
                    raw_dy = curr_y - prev_y
                
                prev_x, prev_y = curr_x, curr_y
                
                # --- Specific Gesture Handling ---
                if gesture == "ZOOM":
                    pinch_y = (hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y + hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y) / 2
                    if prev_pinch_dist is not None:
                        raw_dz = pinch_y - prev_pinch_dist
                    prev_pinch_dist = pinch_y
                else:
                    prev_pinch_dist = None
                    
                if gesture == "ROTATE_OR_ROLL":
                    index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                    pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]
                    curr_roll_angle = math.degrees(math.atan2(pinky_mcp.y - index_mcp.y, pinky_mcp.x - index_mcp.x))
                    
                    if prev_roll_angle is not None:
                        angle_diff = curr_roll_angle - prev_roll_angle
                        if angle_diff > 180: angle_diff -= 360
                        if angle_diff < -180: angle_diff += 360
                        if abs(angle_diff) > 2.0:
                            raw_droll = angle_diff / 100.0
                            gesture = "ROLL"
                        else:
                            gesture = "ROTATE"
                    else:
                        gesture = "ROTATE"
                    prev_roll_angle = curr_roll_angle
                else:
                    prev_roll_angle = None
                    
                # Laser Pointer OS Control
                if "LASER" in gesture and os_windows:
                    # Smooth absolute cursor position based on Index Tip
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    # Map to screen (add a bit of padding to reach edges easily)
                    screen_x = int(max(0, min(1, (index_tip.x - 0.1) / 0.8)) * SCREEN_WIDTH)
                    screen_y = int(max(0, min(1, (index_tip.y - 0.1) / 0.8)) * SCREEN_HEIGHT)
                    user32.SetCursorPos(screen_x, screen_y)
                    
                    if gesture == "LASER_CLICK" and not mouse_clicked:
                        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        mouse_clicked = True
                    elif gesture == "LASER_HOVER":
                        mouse_clicked = False

            else:
                prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
        else:
            prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
            
        raw_dx = apply_deadzone_and_scale(raw_dx)
        raw_dy = apply_deadzone_and_scale(raw_dy)
        raw_dz = apply_deadzone_and_scale(raw_dz)

        speed = math.sqrt(raw_dx**2 + raw_dy**2 + raw_dz**2 + raw_droll**2)
        dynamic_alpha = max(0.1, min(1.0, speed * 80.0))

        ema_dx = (dynamic_alpha * raw_dx) + ((1 - dynamic_alpha) * ema_dx)
        ema_dy = (dynamic_alpha * raw_dy) + ((1 - dynamic_alpha) * ema_dy)
        ema_dz = (dynamic_alpha * raw_dz) + ((1 - dynamic_alpha) * ema_dz)
        ema_droll = (dynamic_alpha * raw_droll) + ((1 - dynamic_alpha) * ema_droll)

        # Network Messaging
        events = ["FIT", "RESET_VIEW", "MACRO_UNDO", "MACRO_SAVE"]
        if gesture in events and event_cooldown == 0:
            msg = {"gesture": gesture}
            sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
            event_cooldown = 40 
            
        elif gesture not in events and "LASER" not in gesture and gesture != "IDLE":
            if any(abs(v) > 0.0001 for v in [ema_dx, ema_dy, ema_dz, ema_droll]):
                msg = {
                    "gesture": gesture,
                    "dx": ema_dx,
                    "dy": ema_dy,
                    "dz": ema_dz,
                    "droll": ema_droll
                }
                sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))

        # UI Overlay
        cv2.putText(image, f'{gesture}', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.imshow(WINDOW_NAME, image)

        if cv2.waitKey(5) & 0xFF == 27:
            break
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

except KeyboardInterrupt:
    pass
finally:
    print("Shutting down gracefully...")
    cam.stop()
    cv2.destroyAllWindows()
    sock.close()
