import cv2
import mediapipe as mp
import socket
import json
import time
import math
import numpy as np

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

print(f"Starting NX Advanced Gesture Server on {UDP_IP}:{UDP_PORT}")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=1
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Window Configuration
cv2.namedWindow('NX Gesture Overlay', cv2.WINDOW_NORMAL)
cv2.resizeWindow('NX Gesture Overlay', 320, 240)
cv2.setWindowProperty('NX Gesture Overlay', cv2.WND_PROP_TOPMOST, 1)

# State
ema_dx = 0.0
ema_dy = 0.0
ema_dz = 0.0
ema_droll = 0.0
DEADZONE = 0.002

prev_x = None
prev_y = None
prev_pinch_dist = None
prev_roll_angle = None
fit_cooldown = 0

def get_3d_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def detect_gesture_advanced(hand_landmarks):
    # Base (MCP) landmarks
    index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
    palm_size = get_3d_distance(index_mcp, pinky_mcp)
    
    # Tip landmarks
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    
    # Check open vs closed fingers (excluding thumb)
    open_count = 0
    if get_3d_distance(index_tip, wrist) > get_3d_distance(index_mcp, wrist) * 1.2: open_count += 1
    if get_3d_distance(middle_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist) * 1.2: open_count += 1
    if get_3d_distance(ring_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP], wrist) * 1.2: open_count += 1
    if get_3d_distance(pinky_tip, wrist) > get_3d_distance(pinky_mcp, wrist) * 1.2: open_count += 1
    
    pinch_dist = get_3d_distance(thumb_tip, index_tip) / palm_size
    
    # "FIT" Gesture (OK Sign: Index & Thumb pinched, other 3 fingers open)
    if pinch_dist < 0.6 and open_count >= 2:
        return "FIT"
        
    # ZOOM Gesture (Pinch but other fingers are NOT fully open, typically a tight pinch)
    if pinch_dist < 0.6:
        return "ZOOM"
        
    if open_count <= 1:
        # Check if wrist is twisting significantly for ROLL
        dy_knuckles = pinky_mcp.y - index_mcp.y
        dx_knuckles = pinky_mcp.x - index_mcp.x
        angle = math.degrees(math.atan2(dy_knuckles, dx_knuckles))
        # If angle is steep, it's mostly a rotation, but we'll track the delta later
        return "ROTATE_OR_ROLL"
    elif open_count >= 3:
        return "PAN"
        
    return "IDLE"

def apply_deadzone_and_scale(val):
    if abs(val) < DEADZONE:
        return 0.0
    sign = 1 if val > 0 else -1
    return sign * (abs(val) ** 1.3) # Increased exponential for better fast control

print("Camera initialized. Overlay started.")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        gesture = "IDLE"
        raw_dx, raw_dy, raw_dz, raw_droll = 0.0, 0.0, 0.0, 0.0

        if fit_cooldown > 0:
            fit_cooldown -= 1

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
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
                        # Handle wrapping around -180/180
                        if angle_diff > 180: angle_diff -= 360
                        if angle_diff < -180: angle_diff += 360
                        
                        if abs(angle_diff) > 2.0: # Significant twist
                            raw_droll = angle_diff / 100.0 # Normalize
                            gesture = "ROLL"
                        else:
                            gesture = "ROTATE"
                    else:
                        gesture = "ROTATE"
                    prev_roll_angle = curr_roll_angle
                else:
                    prev_roll_angle = None
                    
                break 
        else:
            prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
            
        raw_dx = apply_deadzone_and_scale(raw_dx)
        raw_dy = apply_deadzone_and_scale(raw_dy)
        raw_dz = apply_deadzone_and_scale(raw_dz)

        # Dynamic EMA Calculation: 
        # Fast movement = High Alpha (low latency). Slow movement = Low Alpha (smooth).
        speed = math.sqrt(raw_dx**2 + raw_dy**2 + raw_dz**2 + raw_droll**2)
        dynamic_alpha = max(0.1, min(1.0, speed * 80.0))

        ema_dx = (dynamic_alpha * raw_dx) + ((1 - dynamic_alpha) * ema_dx)
        ema_dy = (dynamic_alpha * raw_dy) + ((1 - dynamic_alpha) * ema_dy)
        ema_dz = (dynamic_alpha * raw_dz) + ((1 - dynamic_alpha) * ema_dz)
        ema_droll = (dynamic_alpha * raw_droll) + ((1 - dynamic_alpha) * ema_droll)

        if gesture == "FIT" and fit_cooldown == 0:
            msg = {"gesture": "FIT"}
            sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
            fit_cooldown = 30 # Prevent spamming FIT command
        elif gesture != "IDLE" and gesture != "FIT":
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
        cv2.putText(image, f'Smooth: {dynamic_alpha:.2f}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        cv2.imshow('NX Gesture Overlay', image)

        if cv2.waitKey(5) & 0xFF == 27:
            break
except KeyboardInterrupt:
    pass

cap.release()
cv2.destroyAllWindows()
sock.close()
