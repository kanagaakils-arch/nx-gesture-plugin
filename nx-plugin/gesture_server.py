import cv2
import mediapipe as mp
import socket
import json
import time
import math
import threading
import sys
import os

# Load Configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found.")
    sys.exit(1)

UDP_IP = config["network"]["udp_ip"]
UDP_PORT = config["network"]["udp_port"]
TARGET_HAND = config["tracking"]["target_hand"]
DEADZONE = config["tracking"]["deadzone"]

print(f"Starting NX Advanced Gesture Server on {UDP_IP}:{UDP_PORT}")
print(f"Tracking exclusively for: {TARGET_HAND} hand")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Camera Multithreading Class for high FPS
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
            time.sleep(0.01) # Small sleep to prevent maxing out CPU

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
    max_num_hands=2 # We detect 2 to filter properly
)

cam = CameraStream()

# Window Configuration
WINDOW_NAME = 'NX Gesture Overlay'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 320, 240)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

# State
ema_dx, ema_dy, ema_dz, ema_droll = 0.0, 0.0, 0.0, 0.0
prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
event_cooldown = 0

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
    
    open_count = 0
    if get_3d_distance(index_tip, wrist) > get_3d_distance(index_mcp, wrist) * 1.2: open_count += 1
    if get_3d_distance(middle_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist) * 1.2: open_count += 1
    if get_3d_distance(ring_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP], wrist) * 1.2: open_count += 1
    if get_3d_distance(pinky_tip, wrist) > get_3d_distance(pinky_mcp, wrist) * 1.2: open_count += 1
    
    thumb_open = get_3d_distance(thumb_tip, pinky_mcp) > palm_size * 1.5
    pinch_dist = get_3d_distance(thumb_tip, index_tip) / palm_size
    
    # "RESET_VIEW" Gesture (Thumbs Up: Thumb open, all other fingers closed)
    if thumb_open and open_count == 0:
        return "RESET_VIEW"
        
    # "FIT" Gesture (OK Sign: Index & Thumb pinched, other 3 fingers open)
    if pinch_dist < 0.6 and open_count >= 2:
        return "FIT"
        
    # ZOOM Gesture (Pinch but other fingers are NOT fully open, typically a tight pinch)
    if pinch_dist < 0.6:
        return "ZOOM"
        
    if open_count <= 1:
        return "ROTATE_OR_ROLL"
    elif open_count >= 3:
        return "PAN"
        
    return "IDLE"

def apply_deadzone_and_scale(val):
    if abs(val) < DEADZONE: return 0.0
    sign = 1 if val > 0 else -1
    return sign * (abs(val) ** 1.3)

print("Camera and threads initialized. Overlay started.")

try:
    while True:
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
            # Filter for target hand dominance
            target_hand_idx = -1
            for idx, handedness in enumerate(results.multi_handedness):
                # Mediapipe flips Left/Right because we flipped the image earlier!
                # If target is Right, we want the label that Mediapipe calls "Right" (which is actually physically Right)
                label = handedness.classification[0].label
                if label == TARGET_HAND:
                    target_hand_idx = idx
                    break
                    
            if target_hand_idx != -1:
                hand_landmarks = results.multi_hand_landmarks[target_hand_idx]
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                gesture = detect_gesture_advanced(hand_landmarks)
                
                track_point = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                curr_x = track_point.x
                curr_y = track_point.y
                
                if prev_x is not None and prev_y is not None:
                    raw_dx = curr_x - prev_x
                    raw_dy = curr_y - prev_y
                
                prev_x = curr_x
                prev_y = curr_y
                
                if gesture == "ZOOM":
                    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    pinch_y = (thumb_tip.y + index_tip.y) / 2
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
            else:
                prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
        else:
            prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
            
        raw_dx = apply_deadzone_and_scale(raw_dx)
        raw_dy = apply_deadzone_and_scale(raw_dy)
        raw_dz = apply_deadzone_and_scale(raw_dz)

        # Dynamic EMA
        speed = math.sqrt(raw_dx**2 + raw_dy**2 + raw_dz**2 + raw_droll**2)
        dynamic_alpha = max(0.1, min(1.0, speed * 80.0))

        ema_dx = (dynamic_alpha * raw_dx) + ((1 - dynamic_alpha) * ema_dx)
        ema_dy = (dynamic_alpha * raw_dy) + ((1 - dynamic_alpha) * ema_dy)
        ema_dz = (dynamic_alpha * raw_dz) + ((1 - dynamic_alpha) * ema_dz)
        ema_droll = (dynamic_alpha * raw_droll) + ((1 - dynamic_alpha) * ema_droll)

        if gesture in ["FIT", "RESET_VIEW"] and event_cooldown == 0:
            msg = {"gesture": gesture}
            sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
            event_cooldown = 30 # Cooldown to prevent spamming
            
        elif gesture != "IDLE" and gesture not in ["FIT", "RESET_VIEW"]:
            if any(abs(v) > 0.0001 for v in [ema_dx, ema_dy, ema_dz, ema_droll]):
                msg = {
                    "gesture": gesture,
                    "dx": ema_dx,
                    "dy": ema_dy,
                    "dz": ema_dz,
                    "droll": ema_droll
                }
                sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))

        # UI Overlay Data
        cv2.putText(image, f'{gesture}', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        cv2.imshow(WINDOW_NAME, image)

        # Graceful Exit Checks
        # 1. Check if 'Esc' is pressed
        if cv2.waitKey(5) & 0xFF == 27:
            break
            
        # 2. Check if the window was closed via the "X" button
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

except KeyboardInterrupt:
    pass
finally:
    print("Shutting down gracefully...")
    cam.stop()
    cv2.destroyAllWindows()
    sock.close()
