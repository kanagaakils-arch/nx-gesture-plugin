import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "tracking": {"target_hand": "Right", "deadzone": 0.002, "smoothing_base_alpha": 0.3},
            "sensitivity": {"rotate": 3.0, "pan": 100.0, "zoom": 2.0, "roll": 50.0}
        }
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NX Gesture Control Panel")
        self.geometry("350x450")
        self.configure(padx=20, pady=20)
        self.attributes('-topmost', True)
        
        self.config_data = load_config()
        
        ttk.Label(self, text="NX Gesture Control Settings", font=("Helvetica", 14, "bold")).pack(pady=(0, 15))
        
        # Hand Selection
        hand_frame = ttk.Frame(self)
        hand_frame.pack(fill='x', pady=5)
        ttk.Label(hand_frame, text="Target Hand:").pack(side='left')
        self.hand_var = tk.StringVar(value=self.config_data["tracking"]["target_hand"])
        self.hand_cb = ttk.Combobox(hand_frame, textvariable=self.hand_var, values=["Right", "Left"], state="readonly", width=10)
        self.hand_cb.pack(side='right')

        # Deadzone
        self.deadzone_var = self.create_slider("Deadzone (Micro-tremors)", self.config_data["tracking"]["deadzone"], 0.0, 0.02, 0.001)
        
        # Sensitivities
        ttk.Label(self, text="Sensitivities", font=("Helvetica", 11, "bold")).pack(pady=(15, 5), anchor='w')
        self.rot_var = self.create_slider("Rotate", self.config_data["sensitivity"]["rotate"], 0.5, 10.0, 0.5)
        self.pan_var = self.create_slider("Pan", self.config_data["sensitivity"]["pan"], 10.0, 300.0, 10.0)
        self.zoom_var = self.create_slider("Zoom", self.config_data["sensitivity"]["zoom"], 0.5, 10.0, 0.5)
        self.roll_var = self.create_slider("Roll", self.config_data["sensitivity"]["roll"], 10.0, 150.0, 5.0)
        
        # Save Button
        ttk.Button(self, text="Save & Hot-Reload", command=self.apply_changes).pack(pady=20, fill='x')
        
    def create_slider(self, label_text, default_val, from_, to, resolution):
        frame = ttk.Frame(self)
        frame.pack(fill='x', pady=5)
        ttk.Label(frame, text=label_text).pack(anchor='w')
        var = tk.DoubleVar(value=default_val)
        slider = tk.Scale(frame, from_=from_, to=to, resolution=resolution, orient='horizontal', variable=var)
        slider.pack(fill='x')
        return var

    def apply_changes(self):
        self.config_data["tracking"]["target_hand"] = self.hand_var.get()
        self.config_data["tracking"]["deadzone"] = self.deadzone_var.get()
        self.config_data["sensitivity"]["rotate"] = self.rot_var.get()
        self.config_data["sensitivity"]["pan"] = self.pan_var.get()
        self.config_data["sensitivity"]["zoom"] = self.zoom_var.get()
        self.config_data["sensitivity"]["roll"] = self.roll_var.get()
        
        save_config(self.config_data)
        messagebox.showinfo("Success", "Settings saved! The Gesture Engine will reload them instantly.")

if __name__ == "__main__":
    app = ControlPanel()
    app.mainloop()
