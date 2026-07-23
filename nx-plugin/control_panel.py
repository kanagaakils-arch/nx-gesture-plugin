import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import time

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "tracking": {"target_hand": "Right", "deadzone": 0.002, "enable_head_tracking": False},
            "sensitivity": {"rotate": 3.0, "pan": 100.0, "zoom": 2.0, "roll": 50.0},
            "custom_gestures": {"record_request": False, "active_gestures": {}}
        }
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NX Gesture Enterprise Control")
        self.geometry("400x550")
        self.attributes('-topmost', True)
        
        self.config_data = load_config()
        
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # TAB 1: Core Settings
        tab_core = ttk.Frame(notebook)
        notebook.add(tab_core, text='Core Settings')
        self.build_core_tab(tab_core)
        
        # TAB 2: Custom Gestures & AI
        tab_ai = ttk.Frame(notebook)
        notebook.add(tab_ai, text='AI & Gestures')
        self.build_ai_tab(tab_ai)
        
        ttk.Button(self, text="Save & Hot-Reload All", command=self.apply_changes).pack(pady=10, fill='x', padx=20)

    def build_core_tab(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Hand Selection
        hand_frame = ttk.Frame(frame)
        hand_frame.pack(fill='x', pady=5)
        ttk.Label(hand_frame, text="Target Hand:").pack(side='left')
        self.hand_var = tk.StringVar(value=self.config_data["tracking"].get("target_hand", "Right"))
        self.hand_cb = ttk.Combobox(hand_frame, textvariable=self.hand_var, values=["Right", "Left"], state="readonly", width=10)
        self.hand_cb.pack(side='right')

        self.deadzone_var = self.create_slider(frame, "Deadzone", self.config_data["tracking"].get("deadzone", 0.002), 0.0, 0.02, 0.001)
        
        ttk.Label(frame, text="Sensitivities", font=("Helvetica", 10, "bold")).pack(pady=(15, 5), anchor='w')
        self.rot_var = self.create_slider(frame, "Rotate", self.config_data["sensitivity"].get("rotate", 3.0), 0.5, 10.0, 0.5)
        self.pan_var = self.create_slider(frame, "Pan", self.config_data["sensitivity"].get("pan", 100.0), 10.0, 300.0, 10.0)
        self.zoom_var = self.create_slider(frame, "Zoom", self.config_data["sensitivity"].get("zoom", 2.0), 0.5, 10.0, 0.5)
        self.roll_var = self.create_slider(frame, "Roll", self.config_data["sensitivity"].get("roll", 50.0), 10.0, 150.0, 5.0)

    def build_ai_tab(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Head Tracking
        ttk.Label(frame, text="Holographic Head Tracking", font=("Helvetica", 10, "bold")).pack(anchor='w')
        self.head_var = tk.BooleanVar(value=self.config_data["tracking"].get("enable_head_tracking", False))
        ttk.Checkbutton(frame, text="Enable Parallax Camera", variable=self.head_var).pack(anchor='w', pady=5)
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)
        
        # Custom Gesture Creator
        ttk.Label(frame, text="Custom Gesture Creator", font=("Helvetica", 10, "bold")).pack(anchor='w')
        ttk.Label(frame, text="Hold a hand shape in front of the camera, then click Record.", wraplength=350).pack(anchor='w', pady=5)
        
        ttk.Button(frame, text="🔴 Record Gesture", command=self.record_gesture).pack(pady=5)
        
    def create_slider(self, parent, label_text, default_val, from_, to, resolution):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        ttk.Label(frame, text=label_text).pack(anchor='w')
        var = tk.DoubleVar(value=default_val)
        slider = tk.Scale(frame, from_=from_, to=to, resolution=resolution, orient='horizontal', variable=var)
        slider.pack(fill='x')
        return var

    def record_gesture(self):
        name = simpledialog.askstring("Name Gesture", "Enter a name for this gesture (e.g., MACRO_CUSTOM1):")
        if not name: return
        
        # Tell server to record
        self.config_data["custom_gestures"]["record_request"] = name
        save_config(self.config_data)
        
        messagebox.showinfo("Recording...", "Hold your hand pose steady in front of the camera for 2 seconds!")
        
        # The gesture_server will clear record_request once it saves it

    def apply_changes(self):
        self.config_data["tracking"]["target_hand"] = self.hand_var.get()
        self.config_data["tracking"]["deadzone"] = self.deadzone_var.get()
        self.config_data["tracking"]["enable_head_tracking"] = self.head_var.get()
        
        self.config_data["sensitivity"]["rotate"] = self.rot_var.get()
        self.config_data["sensitivity"]["pan"] = self.pan_var.get()
        self.config_data["sensitivity"]["zoom"] = self.zoom_var.get()
        self.config_data["sensitivity"]["roll"] = self.roll_var.get()
        
        save_config(self.config_data)
        messagebox.showinfo("Success", "Settings hot-reloaded into Gesture Server!")

if __name__ == "__main__":
    app = ControlPanel()
    app.mainloop()
