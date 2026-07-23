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
        self.title("NX Gesture Engine")
        self.geometry("420x600")
        self.attributes('-topmost', True)
        
        self.config_data = load_config()
        self.apply_dark_theme()
        
        # Header
        header = tk.Frame(self, bg="#202225", pady=15)
        header.pack(fill='x')
        tk.Label(header, text="NX GESTURE ENGINE", font=("Segoe UI", 16, "bold"), fg="#00ffcc", bg="#202225").pack()
        tk.Label(header, text="v5.0 Pro Control Panel", font=("Segoe UI", 10), fg="#a8b2b9", bg="#202225").pack()
        
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both', padx=15, pady=15)
        
        # TAB 1: Core Settings
        tab_core = ttk.Frame(notebook)
        notebook.add(tab_core, text='  ⚙️ Core Settings  ')
        self.build_core_tab(tab_core)
        
        # TAB 2: Custom Gestures & AI
        tab_ai = ttk.Frame(notebook)
        notebook.add(tab_ai, text='  🤖 AI & Gestures  ')
        self.build_ai_tab(tab_ai)
        
        # Save Button
        save_btn = tk.Button(self, text="⚡ SAVE & HOT-RELOAD", font=("Segoe UI", 11, "bold"), 
                             bg="#00ffcc", fg="#1e1e1e", activebackground="#00ccaa",
                             relief="flat", cursor="hand2", command=self.apply_changes)
        save_btn.pack(pady=(0, 20), fill='x', padx=30, ipady=8)

    def apply_dark_theme(self):
        self.configure(bg="#2f3136")
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = "#36393f"
        fg_color = "#ffffff"
        accent_color = "#00ffcc"
        
        style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TNotebook", background="#2f3136", borderwidth=0)
        style.configure("TNotebook.Tab", background="#202225", foreground="#a8b2b9", padding=[15, 8], font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", bg_color)], foreground=[("selected", accent_color)])
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TScale", background=bg_color, troughcolor="#202225")
        style.configure("TCombobox", fieldbackground="#202225", foreground=fg_color, background=bg_color)
        style.configure("Separator.TSeparator", background="#4f545c")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=accent_color, foreground="#1e1e1e")

    def build_core_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Hand Selection
        hand_frame = ttk.Frame(frame)
        hand_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(hand_frame, text="Active Hand:", font=("Segoe UI", 11, "bold"), foreground="#00ffcc").pack(side='left')
        self.hand_var = tk.StringVar(value=self.config_data["tracking"].get("target_hand", "Right"))
        self.hand_cb = ttk.Combobox(hand_frame, textvariable=self.hand_var, values=["Right", "Left"], state="readonly", width=12)
        self.hand_cb.pack(side='right')

        ttk.Separator(frame, orient='horizontal', style="Separator.TSeparator").pack(fill='x', pady=10)
        
        ttk.Label(frame, text="Tracking Noise Filter (One-Euro)", font=("Segoe UI", 11, "bold"), foreground="#00ffcc").pack(anchor='w', pady=(5, 0))
        self.deadzone_var = self.create_slider(frame, "Micro-tremor Deadzone", self.config_data["tracking"].get("deadzone", 0.002), 0.0, 0.02, 0.001)
        
        ttk.Separator(frame, orient='horizontal', style="Separator.TSeparator").pack(fill='x', pady=15)
        
        ttk.Label(frame, text="Movement Sensitivities", font=("Segoe UI", 11, "bold"), foreground="#00ffcc").pack(anchor='w', pady=(5, 5))
        self.rot_var = self.create_slider(frame, "Orbit (Rotate)", self.config_data["sensitivity"].get("rotate", 3.0), 0.5, 10.0, 0.5)
        self.pan_var = self.create_slider(frame, "Pan", self.config_data["sensitivity"].get("pan", 100.0), 10.0, 300.0, 10.0)
        self.zoom_var = self.create_slider(frame, "Zoom", self.config_data["sensitivity"].get("zoom", 2.0), 0.5, 10.0, 0.5)
        self.roll_var = self.create_slider(frame, "Roll", self.config_data["sensitivity"].get("roll", 50.0), 10.0, 150.0, 5.0)

    def build_ai_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="Holographic Head Tracking", font=("Segoe UI", 11, "bold"), foreground="#00ffcc").pack(anchor='w')
        ttk.Label(frame, text="Tracks your face to create a 3D parallax effect.", foreground="#a8b2b9").pack(anchor='w', pady=(2, 10))
        self.head_var = tk.BooleanVar(value=self.config_data["tracking"].get("enable_head_tracking", False))
        ttk.Checkbutton(frame, text="Enable Parallax Mode", variable=self.head_var).pack(anchor='w')
        
        ttk.Separator(frame, orient='horizontal', style="Separator.TSeparator").pack(fill='x', pady=20)
        
        ttk.Label(frame, text="Custom Gesture Training", font=("Segoe UI", 11, "bold"), foreground="#00ffcc").pack(anchor='w')
        ttk.Label(frame, text="1. Shape your hand\n2. Click Record\n3. Hold steady for 2 seconds", foreground="#a8b2b9", justify="left").pack(anchor='w', pady=(5, 15))
        
        record_btn = tk.Button(frame, text="🔴 Record New Gesture", font=("Segoe UI", 10, "bold"),
                               bg="#ed4245", fg="#ffffff", activebackground="#c93639",
                               relief="flat", cursor="hand2", command=self.record_gesture)
        record_btn.pack(fill='x', ipady=5)
        
    def create_slider(self, parent, label_text, default_val, from_, to, resolution):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=4)
        ttk.Label(frame, text=label_text).pack(side='left')
        var = tk.DoubleVar(value=default_val)
        slider = ttk.Scale(frame, from_=from_, to=to, orient='horizontal', variable=var)
        slider.pack(side='right', fill='x', expand=True, padx=(15, 0))
        return var

    def record_gesture(self):
        name = simpledialog.askstring("Name Gesture", "Enter a unique name for this gesture\n(e.g., MACRO_EXTRUDE):")
        if not name: return
        
        self.config_data["custom_gestures"]["record_request"] = name
        save_config(self.config_data)
        messagebox.showinfo("Recording...", "Hold your hand pose steady in front of the camera for 2 seconds!")

    def apply_changes(self):
        self.config_data["tracking"]["target_hand"] = self.hand_var.get()
        self.config_data["tracking"]["deadzone"] = self.deadzone_var.get()
        self.config_data["tracking"]["enable_head_tracking"] = self.head_var.get()
        
        self.config_data["sensitivity"]["rotate"] = self.rot_var.get()
        self.config_data["sensitivity"]["pan"] = self.pan_var.get()
        self.config_data["sensitivity"]["zoom"] = self.zoom_var.get()
        self.config_data["sensitivity"]["roll"] = self.roll_var.get()
        
        save_config(self.config_data)

if __name__ == "__main__":
    app = ControlPanel()
    app.mainloop()
