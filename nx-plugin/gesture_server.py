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
import numpy as np
from datetime import datetime

try:
    import winsound
    has_winsound = True
except ImportError:
    has_winsound = False

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "system_log.txt")
last_config_mtime = 0
config = {}

def write_log(msg):
    try:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}\n"
        with open(LOG_FILE, 'a') as f:
            f.write(line)
        # Trim log to 50 lines to avoid bloat
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        if len(lines) > 50:
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines[-50:])
    except:
        pass

def play_audio_cue(cue_type):
    if not has_winsound or not config.get("haptics", {}).get("audio_feedback", True):
        return
    def play():
        if cue_type == "MACRO": winsound.Beep(1200, 100)
        elif cue_type == "MODE_SWITCH": winsound.Beep(800, 150)
        elif cue_type == "STARTUP":
            winsound.Beep(600, 100)
            time.sleep(0.05)
            winsound.Beep(900, 150)
    threading.Thread(target=play, daemon=True).start()

def load_config():
    global config, UDP_IP, UDP_PORT, TARGET_HAND, DEADZONE, ENABLE_HEAD_TRACK, TWO_HAND_MODE, DEPTH_ADAPTIVE, last_config_mtime
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        UDP_IP = config["network"]["udp_ip"]
        UDP_PORT = config["network"]["udp_port"]
        TARGET_HAND = config["tracking"]["target_hand"]
        DEADZONE = config["tracking"]["deadzone"]
        ENABLE_HEAD_TRACK = config["tracking"].get("enable_head_tracking", False)
        TWO_HAND_MODE = config["tracking"].get("two_handed_mode", True)
        DEPTH_ADAPTIVE = config["tracking"].get("depth_adaptive", True)
        last_config_mtime = os.path.getmtime(CONFIG_FILE)
        write_log("Configuration hot-reloaded.")
    except Exception as e:
        pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

write_log("Initializing NX Enterprise Gesture Server...")
load_config()
play_audio_cue("STARTUP")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
write_log(f"UDP Socket Bound: {UDP_IP}:{UDP_PORT}")

try:
    user32 = ctypes.windll.user32
    SCREEN_WIDTH, SCREEN_HEIGHT = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    os_windows = True
except AttributeError:
    os_windows = False
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

class OneEuroFilter:
    def __init__(self, t0, x0, dx0=0.0, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = x0
        self.dx_prev = dx0
        self.t_prev = t0

    def smoothing_factor(self, t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def exponential_smoothing(self, a, x, x_prev):
        return a * x + (1 - a) * x_prev

    def __call__(self, t, x):
        t_e = t - self.t_prev
        if t_e <= 0.0: return x
        
        a_d = self.smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = self.exponential_smoothing(a_d, dx, self.dx_prev)

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self.smoothing_factor(t_e, cutoff)
        x_hat = self.exponential_smoothing(a, x, self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat

class CameraStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.grabbed, self.frame = self.cap.read()
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
    def update(self):
        while self.running:
            grabbed, frame = self.cap.read()
            if grabbed: self.frame = frame
            time.sleep(0.01)
    def read(self):
        return self.grabbed, self.frame
    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=2)
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_faces=1)

cam = CameraStream()

WINDOW_NAME = 'NX Gesture Interface'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 800, 600)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

filter_x = None
filter_y = None
filter_z = None
filter_roll = None

prev_nose_x, prev_nose_y = None, None
event_cooldown = 0
mode_assembly = False
prev_two_hand_dist = None

def get_3d_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)
    
def get_angle(p1, p2, p3):
    v1 = [p1.x - p2.x, p1.y - p2.y, p1.z - p2.z]
    v2 = [p3.x - p2.x, p3.y - p2.y, p3.z - p2.z]
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
    if mag1 * mag2 == 0: return 0
    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_angle))

def extract_hand_features(hand_landmarks):
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    palm_size = get_3d_distance(hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP], hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP])
    features = []
    for lm in hand_landmarks.landmark:
        features.append(get_3d_distance(wrist, lm) / (palm_size + 0.0001))
    return features

def match_custom_gestures(features):
    best_match = "IDLE"
    best_dist = 999.0
    for name, saved_features in config.get("custom_gestures", {}).get("active_gestures", {}).items():
        if len(features) == len(saved_features):
            dist = sum(abs(f - sf) for f, sf in zip(features, saved_features))
            if dist < 1.5 and dist < best_dist:
                best_dist = dist
                best_match = name
    return best_match

def is_pinched(hand_landmarks):
    lm = hand_landmarks.landmark
    palm_size = get_3d_distance(lm[5], lm[17])
    pinch_dist = get_3d_distance(lm[4], lm[8]) / (palm_size + 0.0001)
    return pinch_dist < 0.6

def detect_gesture_advanced(hand_landmarks):
    lm = hand_landmarks.landmark
    
    idx_angle = get_angle(lm[5], lm[6], lm[8])
    mid_angle = get_angle(lm[9], lm[10], lm[12])
    rng_angle = get_angle(lm[13], lm[14], lm[16])
    pnk_angle = get_angle(lm[17], lm[18], lm[20])
    
    idx_up = idx_angle > 140
    mid_up = mid_angle > 140
    rng_up = rng_angle > 140
    pnk_up = pnk_angle > 140
    
    palm_size = get_3d_distance(lm[5], lm[17])
    thumb_open = get_3d_distance(lm[4], lm[17]) > palm_size * 1.5
    pinch_dist = get_3d_distance(lm[4], lm[8]) / (palm_size + 0.0001)
    open_count = sum([idx_up, mid_up, rng_up, pnk_up])
    
    if thumb_open and open_count == 0 and pinch_dist > 1.5: return "MODE_SWITCH"
    if idx_up and mid_up and not rng_up and not pnk_up and not thumb_open: return "MACRO_UNDO" 
    if idx_up and pnk_up and thumb_open and not mid_up and not rng_up: return "MACRO_SAVE" 
    if thumb_open and open_count == 0: return "RESET_VIEW" 
        
    if idx_up and not mid_up and not rng_up and not pnk_up:
        if pinch_dist < 0.6: return "LASER_CLICK"
        return "LASER_HOVER"
        
    if pinch_dist < 0.6 and open_count >= 2: return "FIT" 
    if pinch_dist < 0.6: return "ZOOM"
    if open_count <= 1: return "ROTATE_OR_ROLL" 
    elif open_count >= 3: return "PAN" 
        
    return "IDLE"

def apply_deadzone_and_scale(val):
    if abs(val) < DEADZONE: return 0.0
    sign = 1 if val > 0 else -1
    return sign * (abs(val) ** 1.3)

def draw_hud(image, gesture, mode_assembly, raw_dx, raw_dy, raw_dz, event_cooldown, loop_time):
    overlay = image.copy()
    
    # Top bar
    cv2.rectangle(overlay, (0, 0), (image.shape[1], 60), (20, 20, 20), -1)
    
    # Mode indicator
    mode_color = (0, 165, 255) if mode_assembly else (0, 255, 255)
    mode_text = "ASSEMBLY MODE" if mode_assembly else "CAMERA MODE"
    cv2.putText(overlay, mode_text, (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1.0, mode_color, 2)
    
    # Gesture indicator
    cv2.putText(overlay, f"ACTION: {gesture}", (400, 40), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
    
    # Telemetry Bottom panel
    h, w = image.shape[:2]
    cv2.rectangle(overlay, (0, h-80), (550, h), (20, 20, 20), -1)
    fps = int(1.0 / (loop_time + 0.001))
    cv2.putText(overlay, f"FPS:{fps:02}  dX:{raw_dx:.3f} dY:{raw_dy:.3f} dZ:{raw_dz:.3f}", (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Cooldown Bar
    if event_cooldown > 0:
        cv2.rectangle(overlay, (w//2 - 100, h - 50), (w//2 + 100, h - 30), (50, 50, 50), -1)
        fill_width = int(200 * (event_cooldown / 40.0))
        cv2.rectangle(overlay, (w//2 - 100, h - 50), (w//2 - 100 + fill_width, h - 30), (0, 0, 255), -1)
        cv2.putText(overlay, "COOLDOWN", (w//2 - 40, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)

try:
    write_log("Starting main tracking loop.")
    t_prev = time.time()
    while True:
        if os.path.getmtime(CONFIG_FILE) > last_config_mtime: load_config()

        success, image = cam.read()
        if not success: continue

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = hands.process(image_rgb)
        
        gesture = "IDLE"
        raw_dx, raw_dy, raw_dz, raw_droll = 0.0, 0.0, 0.0, 0.0
        t = time.time()
        loop_time = t - t_prev
        t_prev = t

        if event_cooldown > 0: event_cooldown -= 1
        
        # Head Tracking
        if ENABLE_HEAD_TRACK:
            face_results = face_mesh.process(image_rgb)
            if face_results.multi_face_landmarks:
                face_lm = face_results.multi_face_landmarks[0]
                nose = face_lm.landmark[1]
                if prev_nose_x is not None:
                    hdx = nose.x - prev_nose_x
                    hdy = nose.y - prev_nose_y
                    if abs(hdx) > 0.001 or abs(hdy) > 0.001:
                        sock.sendto(json.dumps({"gesture": "HEAD_TRACK", "dx": hdx*0.1, "dy": hdy*0.1}).encode('utf-8'), (UDP_IP, UDP_PORT))
                prev_nose_x, prev_nose_y = nose.x, nose.y
            else:
                prev_nose_x, prev_nose_y = None, None

        if results.multi_hand_landmarks and results.multi_handedness:
            target_hand_lm = None
            off_hand_lm = None
            
            for idx, handedness in enumerate(results.multi_handedness):
                if handedness.classification[0].label == TARGET_HAND:
                    target_hand_lm = results.multi_hand_landmarks[idx]
                else:
                    off_hand_lm = results.multi_hand_landmarks[idx]
                    
            # Check Two-Handed Zoom (iPad Style)
            two_hand_zoom_active = False
            if TWO_HAND_MODE and target_hand_lm and off_hand_lm:
                mp_drawing.draw_landmarks(image, off_hand_lm, mp_hands.HAND_CONNECTIONS, 
                                          mp_drawing.DrawingSpec(color=(255,0,0), thickness=2, circle_radius=2),
                                          mp_drawing.DrawingSpec(color=(255,255,255), thickness=1))
                if is_pinched(target_hand_lm) and is_pinched(off_hand_lm):
                    two_hand_zoom_active = True
                    gesture = "TWO_HAND_ZOOM"
                    p1 = target_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    p2 = off_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    dist = get_3d_distance(p1, p2)
                    
                    if filter_z is None: filter_z = OneEuroFilter(t, dist, min_cutoff=0.001, beta=100.0)
                    smooth_dist = filter_z(t, dist)
                    
                    if prev_two_hand_dist is not None:
                        raw_dz = smooth_dist - prev_two_hand_dist
                    prev_two_hand_dist = smooth_dist
                    
                    cv2.line(image, (int(p1.x*image.shape[1]), int(p1.y*image.shape[0])), 
                                    (int(p2.x*image.shape[1]), int(p2.y*image.shape[0])), (0,255,255), 3)
            else:
                prev_two_hand_dist = None
                    
            if target_hand_lm and not two_hand_zoom_active:
                mp_drawing.draw_landmarks(image, target_hand_lm, mp_hands.HAND_CONNECTIONS, 
                                          mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                                          mp_drawing.DrawingSpec(color=(255,255,255), thickness=1))
                
                record_req = config.get("custom_gestures", {}).get("record_request", False)
                if record_req:
                    config["custom_gestures"]["active_gestures"][record_req] = extract_hand_features(target_hand_lm)
                    config["custom_gestures"]["record_request"] = False
                    save_config()
                    write_log(f"Recorded custom gesture: {record_req}")
                    play_audio_cue("MACRO")
                
                gesture = detect_gesture_advanced(target_hand_lm)
                if gesture == "IDLE": gesture = match_custom_gestures(extract_hand_features(target_hand_lm))
                
                palm_size = get_3d_distance(target_hand_lm.landmark[5], target_hand_lm.landmark[17])
                # Depth Normalization (further away = smaller palm = multiply dx by inverse)
                depth_multiplier = (0.1 / (palm_size + 0.001)) if DEPTH_ADAPTIVE else 1.0
                
                track_point = target_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                curr_x, curr_y = track_point.x, track_point.y
                
                if filter_x is None:
                    filter_x = OneEuroFilter(t, curr_x, min_cutoff=0.001, beta=100.0)
                    filter_y = OneEuroFilter(t, curr_y, min_cutoff=0.001, beta=100.0)
                    filter_z = OneEuroFilter(t, 0.0, min_cutoff=0.001, beta=100.0)
                    filter_roll = OneEuroFilter(t, 0.0, min_cutoff=0.001, beta=100.0)
                
                smooth_x = filter_x(t, curr_x)
                smooth_y = filter_y(t, curr_y)
                
                if prev_x is not None:
                    raw_dx = (smooth_x - prev_x) * depth_multiplier
                    raw_dy = (smooth_y - prev_y) * depth_multiplier
                prev_x, prev_y = smooth_x, smooth_y
                
                if gesture == "ZOOM":
                    pinch_y = (target_hand_lm.landmark[mp_hands.HandLandmark.THUMB_TIP].y + target_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y) / 2
                    smooth_z = filter_z(t, pinch_y)
                    if prev_pinch_dist is not None:
                        raw_dz = smooth_z - prev_pinch_dist
                    prev_pinch_dist = smooth_z
                else:
                    prev_pinch_dist = None
                    
                if gesture == "ROTATE_OR_ROLL":
                    index_mcp = target_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                    pinky_mcp = target_hand_lm.landmark[mp_hands.HandLandmark.PINKY_MCP]
                    curr_roll_angle = math.degrees(math.atan2(pinky_mcp.y - index_mcp.y, pinky_mcp.x - index_mcp.x))
                    smooth_roll = filter_roll(t, curr_roll_angle)
                    if prev_roll_angle is not None:
                        angle_diff = smooth_roll - prev_roll_angle
                        if angle_diff > 180: angle_diff -= 360
                        if angle_diff < -180: angle_diff += 360
                        if abs(angle_diff) > 2.0:
                            raw_droll = angle_diff / 100.0
                            gesture = "ROLL"
                        else: gesture = "ROTATE"
                    else: gesture = "ROTATE"
                    prev_roll_angle = smooth_roll
                else:
                    prev_roll_angle = None
                    
                if "LASER" in gesture and os_windows:
                    index_tip = target_hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    screen_x = int(max(0, min(1, (index_tip.x - 0.1) / 0.8)) * SCREEN_WIDTH)
                    screen_y = int(max(0, min(1, (index_tip.y - 0.1) / 0.8)) * SCREEN_HEIGHT)
                    user32.SetCursorPos(screen_x, screen_y)
                    
                    cx, cy = int(index_tip.x * image.shape[1]), int(index_tip.y * image.shape[0])
                    cv2.circle(image, (cx, cy), 15, (0, 0, 255), 2)
                    cv2.line(image, (cx-25, cy), (cx+25, cy), (0, 0, 255), 1)
                    cv2.line(image, (cx, cy-25), (cx, cy+25), (0, 0, 255), 1)
                    
                    if gesture == "LASER_CLICK":
                        user32.mouse_event(0x0002, 0, 0, 0, 0)
                        user32.mouse_event(0x0004, 0, 0, 0, 0)

            else:
                if not two_hand_zoom_active:
                    prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
                    filter_x, filter_y, filter_z, filter_roll = None, None, None, None
        else:
            prev_x, prev_y, prev_pinch_dist, prev_roll_angle = None, None, None, None
            prev_two_hand_dist = None
            filter_x, filter_y, filter_z, filter_roll = None, None, None, None
            
        final_dx = apply_deadzone_and_scale(raw_dx)
        final_dy = apply_deadzone_and_scale(raw_dy)
        final_dz = apply_deadzone_and_scale(raw_dz)

        if gesture == "MODE_SWITCH" and event_cooldown == 0:
            mode_assembly = not mode_assembly
            msg = {"gesture": "MODE_SWITCH", "assembly_mode": mode_assembly}
            sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
            event_cooldown = 40
            write_log(f"Fired: MODE_SWITCH (Assembly={mode_assembly})")
            play_audio_cue("MODE_SWITCH")
            
        elif gesture in ["FIT", "RESET_VIEW", "MACRO_UNDO", "MACRO_SAVE"] or gesture.startswith("MACRO_"):
            if event_cooldown == 0:
                msg = {"gesture": gesture}
                sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
                event_cooldown = 40
                write_log(f"Fired: {gesture}")
                play_audio_cue("MACRO")
            
        elif gesture not in ["IDLE", "MODE_SWITCH", "LASER_HOVER", "LASER_CLICK"]:
            if any(abs(v) > 0.0001 for v in [final_dx, final_dy, final_dz, raw_droll]):
                msg = {
                    "gesture": gesture if gesture != "TWO_HAND_ZOOM" else "ZOOM",
                    "dx": final_dx,
                    "dy": final_dy,
                    "dz": final_dz,
                    "droll": raw_droll,
                    "assembly_mode": mode_assembly
                }
                sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))

        draw_hud(image, gesture, mode_assembly, final_dx, final_dy, final_dz, event_cooldown, loop_time)
        cv2.imshow(WINDOW_NAME, image)

        if cv2.waitKey(5) & 0xFF == 27: break
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1: break

except KeyboardInterrupt: pass
finally:
    write_log("Server shutting down.")
    cam.stop()
    cv2.destroyAllWindows()
    sock.close()
