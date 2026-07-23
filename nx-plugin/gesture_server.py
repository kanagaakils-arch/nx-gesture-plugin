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

# Smoothing state
ema_dx = 0.0
ema_dy = 0.0
ema_dz = 0.0
ALPHA = 0.3  # EMA smoothing factor (lower = smoother but more latency)
DEADZONE = 0.002 # Ignore tiny movements

prev_x = None
prev_y = None
prev_pinch_dist = None

def get_3d_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def detect_gesture_advanced(hand_landmarks):
    # Base (MCP) landmarks
    index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
    # Palm size for normalization
    palm_size = get_3d_distance(index_mcp, pinky_mcp)
    
    # Tip landmarks
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    
    # Check Pinch
    pinch_dist = get_3d_distance(thumb_tip, index_tip) / palm_size
    if pinch_dist < 0.8:
        return "ZOOM"
        
    # Check open vs closed fingers using distances from wrist
    fingers_open = 0
    if get_3d_distance(index_tip, wrist) > get_3d_distance(index_mcp, wrist) * 1.2: fingers_open += 1
    if get_3d_distance(middle_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP], wrist) * 1.2: fingers_open += 1
    if get_3d_distance(ring_tip, wrist) > get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP], wrist) * 1.2: fingers_open += 1
    if get_3d_distance(pinky_tip, wrist) > get_3d_distance(pinky_mcp, wrist) * 1.2: fingers_open += 1
    
    if fingers_open <= 1:
        return "ROTATE"
    elif fingers_open >= 3:
        return "PAN"
        
    return "IDLE"

def apply_deadzone_and_scale(val):
    if abs(val) < DEADZONE:
        return 0.0
    # Dynamic scaling: exponential sensitivity for faster movements
    sign = 1 if val > 0 else -1
    return sign * (abs(val) ** 1.2)

print("Camera initialized. Waiting for gestures...")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        gesture = "IDLE"
        raw_dx, raw_dy, raw_dz = 0.0, 0.0, 0.0

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                gesture = detect_gesture_advanced(hand_landmarks)
                
                # Use index MCP for stable tracking point
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
                    # Center of pinch
                    pinch_y = (thumb_tip.y + index_tip.y) / 2
                    if prev_pinch_dist is not None:
                        # Zoom based on moving the pinched fingers up/down
                        raw_dz = pinch_y - prev_pinch_dist
                    prev_pinch_dist = pinch_y
                else:
                    prev_pinch_dist = None
                    
                break # Only process one hand
        else:
            prev_x = None
            prev_y = None
            prev_pinch_dist = None
            
        # Apply Deadzone and Scaling
        raw_dx = apply_deadzone_and_scale(raw_dx)
        raw_dy = apply_deadzone_and_scale(raw_dy)
        raw_dz = apply_deadzone_and_scale(raw_dz)

        # Apply EMA Smoothing
        ema_dx = (ALPHA * raw_dx) + ((1 - ALPHA) * ema_dx)
        ema_dy = (ALPHA * raw_dy) + ((1 - ALPHA) * ema_dy)
        ema_dz = (ALPHA * raw_dz) + ((1 - ALPHA) * ema_dz)

        if gesture != "IDLE":
            # Send message if there is significant smoothed movement
            if abs(ema_dx) > 0.0001 or abs(ema_dy) > 0.0001 or abs(ema_dz) > 0.0001:
                msg = {
                    "gesture": gesture,
                    "dx": ema_dx,
                    "dy": ema_dy,
                    "dz": ema_dz
                }
                sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))

        # Status text
        status_color = (0, 255, 0)
        if gesture == "ROTATE": status_color = (0, 165, 255)
        elif gesture == "ZOOM": status_color = (255, 0, 0)
        
        cv2.putText(image, f'Gesture: {gesture}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        cv2.putText(image, f'EMA: X:{ema_dx:.3f} Y:{ema_dy:.3f}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow('NX Advanced Gesture Server', image)

        if cv2.waitKey(5) & 0xFF == 27:
            break
except KeyboardInterrupt:
    pass

cap.release()
cv2.destroyAllWindows()
sock.close()
