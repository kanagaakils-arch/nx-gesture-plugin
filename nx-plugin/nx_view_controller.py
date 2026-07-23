import NXOpen
import NXOpen.UF
import socket
import json
import time
import os

def main():
    session = NXOpen.Session.GetSession()
    uf = NXOpen.UF.UFSession.GetUFSession()
    
    work_part = session.Parts.Work
    if work_part is None:
        uf.Ui.SetStatus("No active part to control.")
        return
        
    work_view = session.Parts.Display.ModelingViews.WorkView
    
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    last_config_mtime = 0
    
    def load_config():
        nonlocal last_config_mtime
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            last_config_mtime = os.path.getmtime(config_file)
            return config
        except:
            return None

    config = load_config()
    if not config:
        uf.Ui.SetStatus("Error loading config.json")
        return

    UDP_IP = config["network"]["udp_ip"]
    UDP_PORT = config["network"]["udp_port"]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    
    uf.Ui.SetStatus(f"NX Enterprise Controller Active. Listening on port {UDP_PORT}...")

    try:
        while True:
            try:
                if os.path.getmtime(config_file) > last_config_mtime:
                    new_config = load_config()
                    if new_config:
                        config = new_config
                        uf.Ui.SetStatus("Config Hot-Reloaded in NX!")
                
                ROT_SENSITIVITY = config["sensitivity"]["rotate"]
                PAN_SENSITIVITY = config["sensitivity"]["pan"]
                ZOOM_SENSITIVITY = config["sensitivity"]["zoom"]
                ROLL_SENSITIVITY = config["sensitivity"]["roll"]

                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                
                gesture = msg.get("gesture", "IDLE")
                dx = msg.get("dx", 0.0)
                dy = msg.get("dy", 0.0)
                dz = msg.get("dz", 0.0)
                droll = msg.get("droll", 0.0)
                assembly_mode = msg.get("assembly_mode", False)
                
                needs_update = False
                
                if gesture == "MODE_SWITCH":
                    mode_str = "ASSEMBLY MODE ON" if assembly_mode else "CAMERA MODE ON"
                    uf.Ui.SetStatus(f"Gesture Trigger: {mode_str}")
                    continue

                if gesture == "HEAD_TRACK":
                    # Parallax effect: Slight Pan and Rotate
                    if abs(dx) > 0.001 or abs(dy) > 0.001:
                        uf.View.Pan(work_view.Name, -dx * PAN_SENSITIVITY * 0.1, -dy * PAN_SENSITIVITY * 0.1)
                        center = work_view.AbsoluteOrigin
                        axis_y = NXOpen.Vector3d(0.0, 1.0, 0.0)
                        work_view.Concatenate(1.0, center, axis_y, dx * ROT_SENSITIVITY * 0.5)
                        axis_x = NXOpen.Vector3d(1.0, 0.0, 0.0)
                        work_view.Concatenate(1.0, center, axis_x, dy * ROT_SENSITIVITY * 0.5)
                        needs_update = True
                        
                elif gesture.startswith("MACRO_"):
                    if gesture == "MACRO_UNDO":
                        uf.Ui.SetStatus("Gesture Macro: UNDO triggered")
                        try: session.UndoToLastVisibleMark()
                        except: pass
                    elif gesture == "MACRO_SAVE":
                        uf.Ui.SetStatus("Gesture Macro: SAVE triggered")
                        try: work_part.Save(NXOpen.BasePart.SaveComponents.True, NXOpen.BasePart.CloseAfterSave.False)
                        except: pass
                    else:
                        uf.Ui.SetStatus(f"Custom Gesture Triggered: {gesture}")
                
                elif gesture == "RESET_VIEW":
                    work_view.Orient(NXOpen.View.ExtendedViewType.Trimetric)
                    work_view.Fit()
                    needs_update = True
                    
                elif gesture == "FIT":
                    work_view.Fit()
                    needs_update = True
                    
                elif gesture == "ROTATE":
                    if assembly_mode:
                        uf.Ui.SetStatus(f"Assembly Mode: Rotating Component (dx={dx:.2f}, dy={dy:.2f})")
                        # Placeholder for complex assembly rotation builder
                    else:
                        center = work_view.AbsoluteOrigin
                        if abs(dx) > 0.001:
                            axis_y = NXOpen.Vector3d(0.0, 1.0, 0.0)
                            work_view.Concatenate(1.0, center, axis_y, dx * ROT_SENSITIVITY)
                            needs_update = True
                        if abs(dy) > 0.001:
                            axis_x = NXOpen.Vector3d(1.0, 0.0, 0.0)
                            work_view.Concatenate(1.0, center, axis_x, dy * ROT_SENSITIVITY)
                            needs_update = True
                        
                elif gesture == "ROLL":
                    if assembly_mode:
                        uf.Ui.SetStatus(f"Assembly Mode: Rolling Component (droll={droll:.2f})")
                    else:
                        if abs(droll) > 0.001:
                            center = work_view.AbsoluteOrigin
                            axis_z = NXOpen.Vector3d(0.0, 0.0, 1.0)
                            work_view.Concatenate(1.0, center, axis_z, droll * ROLL_SENSITIVITY)
                            needs_update = True
                        
                elif gesture == "PAN":
                    if assembly_mode:
                        uf.Ui.SetStatus(f"Assembly Mode: Moving Component (dx={dx:.2f}, dy={dy:.2f})")
                    else:
                        if abs(dx) > 0.001 or abs(dy) > 0.001:
                            uf.View.Pan(work_view.Name, -dx * PAN_SENSITIVITY, -dy * PAN_SENSITIVITY)
                            needs_update = True
                        
                elif gesture == "ZOOM":
                    if assembly_mode:
                        pass
                    else:
                        if abs(dz) > 0.001:
                            scale = 1.0 + (dz * ZOOM_SENSITIVITY)
                            if scale > 0.1:
                                axis_z = NXOpen.Vector3d(0.0, 0.0, 1.0)
                                work_view.Concatenate(scale, work_view.AbsoluteOrigin, axis_z, 0.0)
                                needs_update = True
                
                if needs_update:
                    uf.Disp.RegenerateDisplay()
                    
            except socket.error:
                pass
            except Exception as e:
                pass
                
            time.sleep(0.01)
            
    except Exception as e:
        uf.Ui.SetStatus("NX Gesture Control Stopped.")

if __name__ == '__main__':
    main()
